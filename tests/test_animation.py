import subprocess
import warnings
from pathlib import Path

import pytest
from PIL import Image

from mosaickit import (
    Animation,
    Canvas,
    CanvasSpec,
    ConfigurationError,
    Parameter,
    RenderError,
    Scene,
    TextLayer,
)
from mosaickit.rendering.matplotlib.animation import play


@pytest.mark.parametrize("use_sweep", [False, True])
def test_animation_construction_warns_once_at_caller(use_sweep):
    p = Parameter("x")
    template = Canvas().add(TextLayer((p, 0), "x"))
    with pytest.warns(DeprecationWarning, match="KineticKit") as caught:
        if use_sweep:
            animation = Animation.sweep(template, p.values([1, 2]))
        else:
            animation = Animation(template, p, (1, 2))
    assert len(caught) == 1
    assert caught[0].category is DeprecationWarning
    assert Path(caught[0].filename) == Path(__file__)
    with warnings.catch_warnings(record=True) as frame_warnings:
        warnings.simplefilter("always")
        assert [frame.layers[0].position[0] for frame in animation.frames()] == [1, 2]
    assert not frame_warnings


@pytest.mark.parametrize("fps", [0, -1, True, 1.5])
def test_animation_retains_fps_validation(fps):
    with pytest.raises(ConfigurationError, match="positive integer"):
        Animation(Canvas(), Parameter("x"), (1,), fps=fps)


def test_animation_retains_empty_values_validation():
    with pytest.raises(ConfigurationError, match="at least one value"):
        Animation(Canvas(), Parameter("x"), ())


def test_sweep_does_not_suppress_unrelated_constructor_warnings():
    class WarningCanvas(Canvas):
        def copy(self):
            warnings.warn("custom copy deprecation", DeprecationWarning, stacklevel=2)
            return super().copy()

    p = Parameter("x")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        Animation.sweep(WarningCanvas(), p.values([1]))
    assert len(caught) == 2
    assert str(caught[0].message) == "custom copy deprecation"
    assert "KineticKit" in str(caught[1].message)


def test_frames_are_backend_neutral_ordered_and_snapshot_isolated():
    p = Parameter("x")
    template = Canvas().add(TextLayer((p, 0), "x"))
    animation = Animation.sweep(template, p.values([1, 2, 3]))
    template.clear()
    frames = list(animation.frames())
    assert all(isinstance(frame, Scene) for frame in frames)
    assert [frame.layers[0].position[0] for frame in frames] == [1, 2, 3]
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


def test_mp4_output_remains_playable_without_repeating_animation_warning(tmp_path):
    from matplotlib.animation import FFMpegWriter

    if not FFMpegWriter.isAvailable():
        pytest.skip("ffmpeg is not installed")
    p = Parameter("x")
    template = Canvas(CanvasSpec(width=2, height=2, dpi=40))
    template.add(TextLayer((p, 5), "moving"))
    with pytest.warns(DeprecationWarning, match="KineticKit"):
        animation = Animation.sweep(template, p.values([1, 5, 9]), fps=2)
    target = tmp_path / "animation.mp4"
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert animation.save(target) == [target]
    assert not any("KineticKit" in str(warning.message) for warning in caught)
    decoded = subprocess.run(
        [FFMpegWriter.bin_path(), "-i", str(target), "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    assert decoded.returncode == 0, decoded.stderr
    assert "frame=    3" in decoded.stderr


def test_mp4_output_retains_missing_ffmpeg_error(monkeypatch, tmp_path):
    from matplotlib.animation import FFMpegWriter

    monkeypatch.setattr(FFMpegWriter, "isAvailable", lambda: False)
    p = Parameter("x")
    with pytest.warns(DeprecationWarning, match="KineticKit"):
        animation = Animation(Canvas(), p, (1,))
    with pytest.raises(RenderError, match="MP4 requires ffmpeg"):
        animation.save(tmp_path / "animation.mp4")


def test_playback_and_save_reject_other_backends(tmp_path):
    class StaticRenderer:
        name = "static"

        def render(self, scene, context):
            return scene

        def save(self, result, target, options):
            return [target]

    p = Parameter("x")
    animation = Animation.sweep(Canvas(renderer=StaticRenderer()), p.values([1]))
    with pytest.raises(RenderError, match="Matplotlib"):
        play(animation)
    with pytest.raises(RenderError, match="animation"):
        animation.save(tmp_path / "bad.gif")
