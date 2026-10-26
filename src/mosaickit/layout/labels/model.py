"""The inputs and results of label placement: labels, obstacles, placements, warnings."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from mosaickit.errors import ConfigurationError
from mosaickit.layout.geometry import Point, Rect, Segment
from mosaickit.layout.labels.options import COMPASS

SPREADS = ("ring", "stack")
"""``ring``: widening rings around the anchor. ``stack``: outward rows along each side (ticks)."""


@dataclass(frozen=True, slots=True)
class Label:
    """A fixed-size box that belongs next to one anchor.

    ``size`` is ``(width, height)`` of the text as it will be drawn; the placer keeps it
    exactly. ``sides`` is the preferred side order (first choice first); a ``stack`` label
    uses only the sides ``"above"``, ``"below"``, ``"left"`` and ``"right"``.
    """

    id: str
    anchor: Point
    size: tuple[float, float]
    sides: Sequence[str] = COMPASS
    spread: str = "ring"
    owner: str | None = None
    """Obstacles whose ``owner`` equals this are the label's own and get ``own_clearance``."""

    def __post_init__(self) -> None:
        if self.spread not in SPREADS:
            raise ConfigurationError(f"Label.spread must be one of {SPREADS}")
        if self.size[0] < 0 or self.size[1] < 0:
            raise ConfigurationError("Label.size must not be negative")
        sides = tuple(self.sides)
        object.__setattr__(self, "sides", sides)
        allowed = (*COMPASS,)
        if any(side not in allowed for side in sides) or not sides:
            raise ConfigurationError(f"Label.sides must be a non-empty subset of {allowed}")

    @property
    def owner_key(self) -> str:
        return self.owner if self.owner is not None else self.id


@dataclass(frozen=True, slots=True)
class Obstacle:
    """Something a label must stay clear of: line segments, or a filled box."""

    segments: tuple[Segment, ...] = ()
    box: Rect | None = None
    owner: str | None = None

    @classmethod
    def polyline(cls, points: Sequence[Point], owner: str | None = None) -> Obstacle:
        pts = list(points)
        if len(pts) == 1:
            return cls(((pts[0], pts[0]),), None, owner)
        return cls(tuple(zip(pts, pts[1:], strict=False)), None, owner)

    @classmethod
    def rect(cls, box: Rect, owner: str | None = None) -> Obstacle:
        return cls((), box, owner)

    @classmethod
    def dot(cls, center: Point, radius: float, owner: str | None = None) -> Obstacle:
        return cls((), Rect.centered(center, 2 * radius, 2 * radius), owner)


@dataclass(frozen=True, slots=True)
class Placement:
    """Where one label went.

    ``offset`` is from the anchor to the near corner/edge of the box that faces it;
    ``side`` is the compass side of the anchor the box is on. ``leader`` joins the anchor to
    the box when the label sits further out than ``LabelOptions.leader_after``. ``ok`` is
    False when no free position was found: the box is then a fallback and a warning exists.
    """

    label_id: str
    box: Rect
    side: str
    offset: Point
    leader: Segment | None
    cost: float
    ok: bool = True
    text_anchor: str = "center"
    """The ``TextLayer.anchor`` that puts the text in ``box`` when its position is the label's
    anchor and its offset is ``offset``."""


@dataclass(frozen=True, slots=True)
class PlacementWarning:
    """A label that could not be placed free of collisions, and why."""

    label_id: str
    reason: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class PlacementResult:
    placements: tuple[Placement, ...]
    warnings: tuple[PlacementWarning, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.warnings

    def by_id(self) -> dict[str, Placement]:
        return {p.label_id: p for p in self.placements}
