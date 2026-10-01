import warnings

import pytest

from mosaickit import (
    CacheBypassWarning,
    CacheKey,
    Canvas,
    CanvasGrid,
    Config,
    GroupLayer,
    PathLayer,
    RenderCache,
    Stroke,
    StyleBundle,
    Theme,
)
from mosaickit.rendering.plan import _build_render_plan


@pytest.mark.parametrize(
    "layer_width,canvas_width,config_width,expected",
    [
        (5, 4, 3, 5),
        (None, 4, 3, 4),
        (None, None, 3, 3),
        (None, None, None, 2),
        (0, 4, 3, 0),
    ],
)
def test_style_precedence(layer_width, canvas_width, config_width, expected):
    canvas = Canvas(
        theme=Theme("test", {"a": StyleBundle(stroke=Stroke(width=2))}),
        config=Config(role_overrides={"a.b": StyleBundle(stroke=Stroke(width=config_width))}),
        role_overrides={"a.b": StyleBundle(stroke=Stroke(width=canvas_width))},
    ).add(PathLayer([(0, 0), (1, 1)], role="a.b", stroke=Stroke(width=layer_width)))
    plan = _build_render_plan(canvas.snapshot(), canvas._context())
    assert plan.layers[0].style.stroke.width == expected


def test_hidden_groups_and_stable_order():
    a = PathLayer([(0, 0), (1, 1)], id="a")
    b = PathLayer([(0, 0), (2, 2)], id="b")
    hidden = PathLayer([(0, 0), (3, 3)], id="hidden")
    canvas = Canvas().extend([GroupLayer((a, b)), GroupLayer((hidden,), visible=False)])
    assert [
        item.layer.id for item in _build_render_plan(canvas.snapshot(), canvas._context()).layers
    ] == ["a", "b"]


def key(model=1, **changes):
    fields = dict(
        layer_id="a", bindings=(), model=model, viewport=(0, 1), tolerance=1e-6, theme_snapshot=()
    )
    fields.update(changes)
    return CacheKey(**fields)


def test_lru_hits_misses_and_eviction():
    cache = RenderCache(max_entries=2)
    assert cache.get_or_create(key(), lambda: 10) == 10
    assert cache.get_or_create(key(), lambda: 20) == 10
    cache.get_or_create(key(2), lambda: 2)
    cache.get_or_create(key(), lambda: 0)
    cache.get_or_create(key(3), lambda: 3)
    assert cache.get_or_create(key(2), lambda: 22) == 22
    assert len(cache) == 2
    assert cache.get_or_create(key(bindings=(1,)), lambda: 99) == 99
    cache.clear()
    assert len(cache) == 0


def test_unhashable_model_warns_once_and_still_renders():
    cache = RenderCache()
    canvas = Canvas().add(PathLayer([(0, 0), (1, 1)], model=[]))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for _ in range(2):
            result = canvas.render(cache=cache)
            result.close()
    relevant = [item for item in caught if issubclass(item.category, CacheBypassWarning)]
    assert len(relevant) == 1
    assert "list" in str(relevant[0].message)
    assert len(cache) == 0


def test_cache_cannot_reuse_different_geometry_with_same_id():
    cache = RenderCache()
    first = Canvas().add(PathLayer([(0, 0), (1, 1)], id="same"))
    second = Canvas().add(PathLayer([(0, 0), (2, 2)], id="same"))
    first_plan = _build_render_plan(first.snapshot(), first._context(cache))
    second_plan = _build_render_plan(second.snapshot(), second._context(cache))
    assert first_plan.layers[0].layer.path != second_plan.layers[0].layer.path


def test_job_cache_is_shared_within_grid_not_between_jobs():
    from mosaickit.rendering.matplotlib import MatplotlibRenderer

    class Recording(MatplotlibRenderer):
        def __init__(self):
            self.caches = []

        def _draw(self, ax, scene, context):
            self.caches.append(context.cache)
            return super()._draw(ax, scene, context)

    renderer = Recording()
    grid = CanvasGrid([Canvas(), Canvas()])
    grid.render(renderer=renderer).close()
    grid.render(renderer=renderer).close()
    assert renderer.caches[0] is renderer.caches[1]
    assert renderer.caches[2] is renderer.caches[3]
    assert renderer.caches[0] is not renderer.caches[2]
    explicit = RenderCache()
    grid.render(renderer=renderer, cache=explicit).close()
    assert renderer.caches[-1] is explicit
