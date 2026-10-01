import pytest
from PIL import Image

from mosaickit import Animation, Canvas, CanvasSpec, Parameter, RenderError, Scene, TextLayer
from mosaickit.rendering.matplotlib.animation import play


def test_frames_are_backend_neutral_ordered_and_snapshot_isolated():
    p = Parameter("x")
    template = Canvas().add(TextLayer((p, 0), "x"))
    animation = Animation.sweep(template, p.values([1, 2, 3]))
    template.clear()
    frames = list(animation.frames())
    assert all(isinstance(frame, Scene) for frame in frames)
    assert [frame.layers[0].position.x for frame in frames] == [1, 2, 3]
    assert len({frame.layers[0].id for frame in frames}) == 1


def test_gif_frame_count_and_shared_cache(tmp_path):
    from mosaickit.rendering.matplotlib import MatplotlibRenderer

    class Recording(MatplotlibRenderer):
        def __init__(self):
            self.caches = []

        def _draw(self, ax, scene, context):
            self.caches.append(context.cache)
            super()._draw(ax, scene, context)

    p = Parameter("x")
    renderer = Recording()
    template = Canvas(CanvasSpec(width=2, height=2, dpi=40), renderer=renderer)
    template.add(TextLayer((p, 5), "moving"))
    animation = Animation.sweep(template, p.values([1, 5, 9]), fps=2)
    target = tmp_path / "animation.gif"
    assert animation.save(target) == [target]
    with Image.open(target) as image:
        assert image.n_frames == 3
    assert all(cache is renderer.caches[0] for cache in renderer.caches)


def test_playback_and_save_reject_other_backends(tmp_path):
    p = Parameter("x")
    animation = Animation.sweep(Canvas(renderer="tikz"), p.values([1]))
    with pytest.raises(RenderError, match="Matplotlib"):
        play(animation)
    with pytest.raises(RenderError, match="animation"):
        animation.save(tmp_path / "bad.gif")
