from pathlib import Path

from matplotlib.animation import AbstractMovieWriter, FFMpegWriter, FuncAnimation, PillowWriter

from mosaickit.errors import RenderError
from mosaickit.rendering.cache import RenderCache


def save_animation(animation, path: Path, renderer, cache) -> list[Path]:
    writer: AbstractMovieWriter
    if path.suffix.lower() == ".gif":
        writer = PillowWriter(fps=animation.fps)
    elif path.suffix.lower() == ".mp4":
        if not FFMpegWriter.isAvailable():
            raise RenderError("MP4 requires ffmpeg on PATH")
        writer = FFMpegWriter(fps=animation.fps)
    else:
        raise RenderError("Animation output must be .gif or .mp4")
    first = animation.template.bind(animation.parameter, animation.values[0])
    result = renderer.render(first.snapshot(), first._context(cache))
    try:
        with writer.saving(result.figure, str(path), animation.template.spec.dpi):
            for value in animation.values:
                bound = animation.template.bind(animation.parameter, value)
                result.axes.clear()
                renderer._draw(result.axes, bound.snapshot(), bound._context(cache))
                writer.grab_frame()
    finally:
        result.close()
    return [path]


def play(animation):
    renderer = animation.template._renderer()
    if renderer.name != "matplotlib":
        raise RenderError("Interactive playback requires the Matplotlib renderer")
    from matplotlib import pyplot as plt

    spec = animation.template.spec
    figure, ax = plt.subplots(figsize=(spec.width, spec.height), dpi=spec.dpi)
    cache = RenderCache()

    def update(value):
        ax.clear()
        canvas = animation.template.bind(animation.parameter, value)
        renderer._draw(ax, canvas.snapshot(), canvas._context(cache))
        return tuple(ax.get_children())

    handle = FuncAnimation(figure, update, frames=animation.values, interval=1000 / animation.fps)
    plt.show(block=False)
    return handle
