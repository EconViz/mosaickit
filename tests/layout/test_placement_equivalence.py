"""The array open area and the lazy callout search give exactly what the old loops gave."""

from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import pytest

from mosaickit.layout import Obstacles, Rect
from mosaickit.layout.placement.callout import place_callout
from mosaickit.layout.placement.open_area import open_area

_spec = importlib.util.spec_from_file_location(
    "reference_placement", Path(__file__).with_name("reference_placement.py")
)
assert _spec is not None and _spec.loader is not None
reference = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = reference
_spec.loader.exec_module(reference)

BOUNDS = Rect(0.0, 0.0, 300.0, 200.0)


def _scene(rng: random.Random, integers: bool) -> Obstacles:
    def coord(top: float) -> float:
        return float(rng.randint(-20, int(top) + 20)) if integers else rng.uniform(-20, top + 20)

    def point() -> tuple[float, float]:
        return (coord(300), coord(200))

    def polygon() -> tuple[tuple[float, float], ...]:
        cx, cy = point()
        size = rng.choice((3, 4, 6, 40))
        return tuple(
            (
                cx + rng.randint(-60, 60) + (0 if integers else rng.random()),
                cy + rng.randint(-40, 40),
            )
            for _ in range(size)
        )

    def rect() -> Rect:
        x0, y0 = point()
        return Rect(x0, y0, x0 + rng.randint(0, 50), y0 + rng.randint(0, 30))

    return Obstacles(
        tuple((point(), point()) for _ in range(rng.randint(0, 80))),
        tuple(rect() for _ in range(rng.randint(0, 8))),
        tuple(polygon() for _ in range(rng.randint(0, 4))),
    )


@pytest.mark.parametrize("trial", range(60))
def test_open_area_matches_the_cell_by_cell_version(trial: int) -> None:
    rng = random.Random(1000 + trial)
    obstacles = _scene(rng, trial % 2 == 0)
    cell = rng.choice((4.0, 7.5, 12.0))
    new = open_area(BOUNDS, obstacles, cell)
    old = reference.reference_open_area(BOUNDS, obstacles, cell)
    assert new.cells == old.cells


@pytest.mark.parametrize("trial", range(60))
def test_place_callout_matches_the_full_scan(trial: int) -> None:
    rng = random.Random(5000 + trial)
    obstacles = _scene(rng, trial % 2 == 0)
    cx, cy = rng.uniform(60, 240), rng.uniform(50, 150)
    own = ((cx - 25, cy - 15), (cx + 25, cy - 15), (cx + 25, cy + 15), (cx - 25, cy + 15))
    size = (rng.uniform(20, 70), rng.uniform(10, 25))
    scale = rng.choice((1.0, 2.0))
    new = place_callout(own, size, obstacles, BOUNDS, scale=scale)
    old = reference.reference_place_callout(own, size, obstacles, BOUNDS, scale=scale)
    assert new == old
