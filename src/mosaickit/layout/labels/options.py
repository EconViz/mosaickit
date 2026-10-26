"""Every distance, count and weight of the label placer, as one frozen dataclass."""

from __future__ import annotations

from dataclasses import dataclass

from mosaickit.errors import ConfigurationError

TICK_STRATEGIES = ("stagger", "opposite", "stagger+opposite")
"""How a colliding tick label moves: further out in rows, to the other side, or both."""

COMPASS = (
    "upper-right",
    "right",
    "lower-right",
    "above",
    "below",
    "upper-left",
    "left",
    "lower-left",
)
"""The eight sides of an anchor; a label's ``sides`` lists them first choice first."""


@dataclass(frozen=True, slots=True)
class LabelOptions:
    """Parameters of :func:`~mosaickit.layout.labels.place_labels`.

    Lengths are in the unit of the scene (points in practice). The placer never changes a
    label's size; none of these fields is a font size.
    """

    gap: float = 5.0
    """Free space between an anchor and the nearest edge of its label on the first ring."""
    clearance: float = 3.5
    """Free space kept between a label box and any obstacle (line, marker, fixed box)."""
    own_clearance: float = 0.0
    """The same for obstacles owned by the label itself (its own marker or curve)."""
    label_gap: float = 2.0
    """Free space kept between two label boxes."""
    ring_step: float = 8.0
    """How much further out each ring of the search sits than the one before."""
    rings: int = 8
    """How many rings the search tries after the first one; 0 tries the compass sides only."""
    ring_directions: int = 16
    """Extra directions per ring, evenly spaced between the compass sides."""
    extra_rank: float = 0.5
    """Steps down the side order charged to an extra direction, on top of the side it lies in."""
    anchor_clearance: float = 2.0
    """Free space kept around the anchor of every other label, so a box never covers it."""
    ownership_margin: float = 1.0
    """A box must be at least this much nearer its own anchor than to any other label's."""
    bounds_margin: float = 0.0
    """Free space kept between a label box and the edge of the bounds."""
    leader_after: float = 24.0
    """A label further than this from its anchor (edge to anchor) is joined to it by a leader."""
    leader_gap: float = 1.5
    """Free space between the end of a leader and the label box."""
    rank_weight: float = 4.0
    """Cost of each step down a label's preferred side order."""
    distance_weight: float = 0.5
    """Cost per unit of distance between the label box and its anchor."""
    leader_weight: float = 20.0
    """Fixed cost of needing a leader."""
    leader_crossing_weight: float = 25.0
    """Cost of each line a leader crosses."""
    unplaced_cost: float = 10_000.0
    """Cost of leaving a label without a free position; large, so it is the last resort."""
    search_budget: int = 1_500
    """Most search nodes expanded before the best placement found so far is returned."""
    domain_limit: int = 48
    """Most free positions kept per label, cheapest first; bounds the search time."""
    tick_strategy: str = "stagger+opposite"
    """One of :data:`TICK_STRATEGIES`: what a colliding tick label does."""
    stack_rows: int = 3
    """Rows a staggered tick label may move out (0 allows none)."""
    row_gap: float = 3.0
    """Free space between two staggered rows."""

    def __post_init__(self) -> None:
        if self.tick_strategy not in TICK_STRATEGIES:
            raise ConfigurationError(f"LabelOptions.tick_strategy must be one of {TICK_STRATEGIES}")
        for name in ("gap", "clearance", "own_clearance", "label_gap", "ring_step", "leader_gap"):
            if getattr(self, name) < 0:
                raise ConfigurationError(f"LabelOptions.{name} must not be negative")
        if self.rings < 0 or self.ring_directions < 1 or self.stack_rows < 0:
            raise ConfigurationError("LabelOptions needs rings >= 0, ring_directions >= 1")
        if self.search_budget < 1 or self.domain_limit < 1:
            raise ConfigurationError("LabelOptions.search_budget, domain_limit must be >= 1")
