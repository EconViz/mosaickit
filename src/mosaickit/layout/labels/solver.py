"""Global choice of one option per label: most constrained first, branch and bound.

Each label has a domain of free options sorted by cost. Two options of different labels
conflict when their boxes (padded by ``label_gap``) overlap, when a leader hits the other
box, or when two leaders cross. The search picks the label with the smallest domain, tries
its options cheapest first, removes the options that now conflict from every other domain
(forward checking) and prunes any branch whose cost plus the cheapest remaining option of each
label cannot beat the best total found. A label may also stay unplaced at ``unplaced_cost``.
Ties break by input order, so the same input always gives the same answer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from mosaickit.layout.geometry import Rect, rect_hits_segment, segments_intersect
from mosaickit.layout.labels.feasibility import Option
from mosaickit.layout.labels.options import LabelOptions


def conflicts(first: Option, second: Option, label_gap: float) -> bool:
    """Whether two options of different labels cannot both be used."""
    a, b = first.box, second.box
    if (
        a.x0 < b.x1 + label_gap
        and b.x0 < a.x1 + label_gap
        and a.y0 < b.y1 + label_gap
        and b.y0 < a.y1 + label_gap
    ):
        return True
    for mine, theirs in ((first, second), (second, first)):
        if mine.leader is not None and rect_hits_segment(theirs.box, *mine.leader):
            return True
    if first.leader is not None and second.leader is not None:
        return segments_intersect(*first.leader, *second.leader)
    return False


@dataclass(slots=True)
class Solution:
    """The chosen option index per label (``None``: unplaced), its total cost, and whether
    the search ran out of its budget before it could prove the choice best."""

    chosen: list[int | None]
    cost: float
    exhausted: bool


class _Search:
    def __init__(self, domains: Sequence[Sequence[Option]], options: LabelOptions) -> None:
        self.domains = domains
        self.o = options
        self.best: Solution | None = None
        self.nodes = 0
        self.exhausted = False
        self._pairs: dict[tuple[int, int, int, int], bool] = {}

    def conflict(self, i: int, a: int, j: int, b: int) -> bool:
        key = (i, a, j, b) if i < j else (j, b, i, a)
        cached = self._pairs.get(key)
        if cached is None:
            cached = conflicts(self.domains[i][a], self.domains[j][b], self.o.label_gap)
            self._pairs[key] = cached
        return cached

    def bound(self, live: dict[int, list[int]]) -> float:
        return sum(
            self.domains[i][opts[0]].cost if opts else self.o.unplaced_cost
            for i, opts in live.items()
        )

    def run(self, live: dict[int, list[int]], chosen: list[int | None], cost: float) -> None:
        self.nodes += 1
        if self.best is not None and (self.nodes > self.o.search_budget):
            self.exhausted = True
            return
        if not live:
            if self.best is None or cost < self.best.cost:
                self.best = Solution(list(chosen), cost, False)
            return
        if self.best is not None and cost + self.bound(live) >= self.best.cost:
            return
        pick = min(live, key=lambda i: (len(live[i]), i))
        rest = {i: opts for i, opts in live.items() if i != pick}
        floor = self.bound(rest)
        for index in live[pick]:
            price = cost + self.domains[pick][index].cost
            if self.best is not None and price + floor >= self.best.cost:
                break  # options are sorted by cost: no later one can win either
            narrowed = {
                j: [b for b in opts if not self.conflict(pick, index, j, b)]
                for j, opts in rest.items()
            }
            chosen[pick] = index
            self.run(narrowed, chosen, price)
            chosen[pick] = None
            if self.exhausted:
                return
        self.run(rest, chosen, cost + self.o.unplaced_cost)


def _reach(domain: Sequence[Option], pad: float) -> Rect | None:
    """The smallest rect holding every box and leader of a domain, padded."""
    if not domain:
        return None
    xs: list[float] = []
    ys: list[float] = []
    for option in domain:
        xs += [option.box.x0, option.box.x1]
        ys += [option.box.y0, option.box.y1]
        if option.leader is not None:
            xs += [option.leader[0][0], option.leader[1][0]]
            ys += [option.leader[0][1], option.leader[1][1]]
    return Rect(min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def components(domains: Sequence[Sequence[Option]], label_gap: float) -> list[list[int]]:
    """Groups of labels that can influence each other (their reaches overlap), in input order.

    Labels in different groups never conflict, so each group is solved on its own.
    """
    reaches = [_reach(d, label_gap) for d in domains]
    seen: set[int] = set()
    groups: list[list[int]] = []
    for start in range(len(domains)):
        if start in seen:
            continue
        group, stack = [], [start]
        seen.add(start)
        while stack:
            i = stack.pop()
            group.append(i)
            ri = reaches[i]
            for j in range(len(domains)):
                rj = reaches[j]
                if j not in seen and ri is not None and rj is not None and ri.intersects(rj):
                    seen.add(j)
                    stack.append(j)
        groups.append(sorted(group))
    return groups


def solve(domains: Sequence[Sequence[Option]], options: LabelOptions) -> Solution:
    """The cheapest conflict-free choice found, group by group, within the node budget."""
    chosen: list[int | None] = [None] * len(domains)
    total = 0.0
    exhausted = False
    for group in components(domains, options.label_gap):
        search = _Search([domains[i] for i in group], options)
        search.run(
            {k: list(range(len(domains[i]))) for k, i in enumerate(group)}, [None] * len(group), 0.0
        )
        assert search.best is not None
        for k, i in enumerate(group):
            chosen[i] = search.best.chosen[k]
        total += search.best.cost
        exhausted = exhausted or search.exhausted
    return Solution(chosen, total, exhausted)
