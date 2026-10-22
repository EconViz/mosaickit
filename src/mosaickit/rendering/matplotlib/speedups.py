"""Work Matplotlib does while a scene is drawn that the result never uses.

Both helpers are scoped to one draw and leave Matplotlib as they found it afterwards.
Neither changes a figure: ``tests/test_matplotlib_speedups.py`` compares drawings made
with and without them, and if a Matplotlib release renames what they rely on they
quietly do nothing.
"""

from __future__ import annotations

import inspect
import threading
from collections import OrderedDict
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import matplotlib
from matplotlib import mathtext
from matplotlib.font_manager import FontProperties

# What mathtext and font lookup read besides the font properties themselves.
_FONT_RC = (
    "font.family",
    "font.sans-serif",
    "font.serif",
    "font.monospace",
    "font.cursive",
    "font.fantasy",
    "font.style",
    "font.variant",
    "font.weight",
    "font.stretch",
    "font.size",
)
_PARSE_PARAMETERS = ["self", "s", "dpi", "prop", "antialiased"]
_CACHE_LIMIT = 8192


def _font_properties(prop: Any) -> FontProperties:
    """The font properties Matplotlib would resolve ``prop`` to (private, so by name)."""
    if prop is None:
        return FontProperties()
    return getattr(FontProperties, "_from_any")(prop)  # noqa: B009


@contextmanager
def without_data_limits(ax: Any) -> Iterator[None]:
    """Skip Matplotlib's data-limit bookkeeping while artists are added to ``ax``.

    The renderer sets both axis limits itself and never autoscales, so the extents that
    ``add_patch`` and ``add_line`` accumulate are never read.
    """
    ax._update_patch_limits = lambda patch: None
    ax._update_line_limits = lambda line: None
    try:
        yield
    finally:
        for name in ("_update_patch_limits", "_update_line_limits"):
            ax.__dict__.pop(name, None)


class _MathtextCache:
    """A value-keyed cache in front of ``MathTextParser.parse``, installed while drawing.

    Matplotlib caches parses by parser instance, and each renderer builds its own, so the
    cache never hits from one figure to the next. The key here holds everything a parse
    depends on: the output type, the string, the dpi, the font properties by value, and
    the mathtext and font rcParams. Drawing under other settings never sees a result
    stored under different ones.
    """

    def __init__(self) -> None:
        self._entries: OrderedDict[tuple[Any, ...], Any] = OrderedDict()
        self._lock = threading.Lock()
        self._users = 0
        self._original: Any = None

    @staticmethod
    def _usable() -> bool:
        try:
            names = list(inspect.signature(mathtext.MathTextParser.parse).parameters)
        except (TypeError, ValueError):
            return False
        return names == _PARSE_PARAMETERS

    def _key(self, parser: Any, s: Any, dpi: Any, prop: Any, antialiased: Any) -> tuple[Any, ...]:
        resolved = _font_properties(prop)
        rc = matplotlib.rcParams
        names = [k for k in rc if k.startswith("mathtext.") or k in _FONT_RC]
        return (
            parser._output_type,
            s,
            dpi,
            (
                tuple(resolved.get_family()),
                resolved.get_style(),
                resolved.get_variant(),
                resolved.get_weight(),
                resolved.get_stretch(),
                resolved.get_size(),
                resolved.get_file(),
                resolved.get_math_fontfamily(),
            ),
            antialiased,
            tuple(
                (k, tuple(v) if isinstance(v, list) else v)
                for k in names
                for v in (dict.__getitem__(rc, k),)
            ),
        )

    def _parse(
        self, parser: Any, s: Any, dpi: Any = 72, prop: Any = None, *, antialiased: Any = None
    ) -> Any:
        try:
            key = self._key(parser, s, dpi, prop, antialiased)
            hash(key)
        except Exception:  # noqa: BLE001 - anything unusual bypasses the cache
            return self._original(parser, s, dpi, prop, antialiased=antialiased)
        with self._lock:
            hit = self._entries.get(key)
            if hit is not None:
                self._entries.move_to_end(key)
                return hit
        result = self._original(parser, s, dpi, prop, antialiased=antialiased)
        with self._lock:
            self._entries[key] = result
            if len(self._entries) > _CACHE_LIMIT:
                self._entries.popitem(last=False)
        return result

    @contextmanager
    def installed(self) -> Iterator[None]:
        if not self._usable():
            yield
            return
        with self._lock:
            if self._users == 0:
                self._original = mathtext.MathTextParser.parse
                cache = self

                def parse(parser, s, dpi=72, prop=None, *, antialiased=None):  # type: ignore[no-untyped-def]
                    return cache._parse(parser, s, dpi, prop, antialiased=antialiased)

                mathtext.MathTextParser.parse = parse  # type: ignore[method-assign]
            self._users += 1
        try:
            yield
        finally:
            with self._lock:
                self._users -= 1
                if self._users == 0:
                    mathtext.MathTextParser.parse = self._original  # type: ignore[method-assign]


mathtext_cache = _MathtextCache()
