from dataclasses import dataclass
from itertools import product
from math import isfinite, fsum
from random import Random

from ..cards import Card, parse_card
from ..range_parser import HandCombo, parse_range


def normalize_board(board):
    cards = tuple(parse_card(c) if isinstance(c, str) else c for c in board)
    if len(cards) != 5 or any(not isinstance(c, Card) for c in cards) or len(set(cards)) != 5:
        raise ValueError("A fixed river board requires five distinct cards")
    return cards


@dataclass(frozen=True)
class WeightedRange:
    entries: tuple[tuple[HandCombo, float], ...]

    def __post_init__(self):
        merged = {}
        for combo, weight in self.entries:
            if not isinstance(combo, HandCombo) or not isfinite(weight) or weight < 0:
                raise ValueError("Expected HandCombo and finite nonnegative weight")
            canonical = HandCombo(*sorted(combo.cards))
            merged[canonical] = merged.get(canonical, 0.0) + weight
        total = fsum(merged.values())
        if not isfinite(total) or total <= 0:
            raise ValueError("Range must have positive finite mass")
        object.__setattr__(self, "entries", tuple((c, w / total) for c, w in merged.items() if w))

    @classmethod
    def from_range(cls, value):
        if isinstance(value, cls):
            return value
        combos = parse_range(value) if isinstance(value, str) else tuple(value)
        # An unweighted range denotes a set, not repeated probability mass.
        combos = dict.fromkeys(HandCombo(*sorted(c.cards)) for c in combos)
        return cls(tuple((c, 1.0) for c in combos))


@dataclass(frozen=True)
class Deal:
    hands: tuple[HandCombo, ...]
    probability: float


class MultiwayDealDistribution:
    """Product range weights conditioned on all eleven cards being distinct."""
    def __init__(self, ranges, board):
        self.board = normalize_board(board)
        if len(ranges) != 3:
            raise ValueError("This research game supports exactly three players")
        self.ranges = tuple(WeightedRange(tuple(
            (c, w) for c, w in WeightedRange.from_range(r).entries
            if not c.overlaps(self.board))) for r in ranges)

    @staticmethod
    def legal(hands):
        return len({c for h in hands for c in h.cards}) == 6

    def exact(self, max_candidates=2_000_000):
        count = 1
        for r in self.ranges:
            count *= len(r.entries)
        if count > max_candidates:
            raise ValueError("Exact enumeration limit exceeded; use sampling")
        rows = []
        for entries in product(*(r.entries for r in self.ranges)):
            hands = tuple(e[0] for e in entries)
            if self.legal(hands):
                rows.append((hands, entries[0][1] * entries[1][1] * entries[2][1]))
        mass = fsum(w for _, w in rows)
        if mass <= 0:
            raise ValueError("No legal positive-mass deals")
        return tuple(Deal(h, w / mass) for h, w in rows)

    def sample(self, n, seed=None, max_attempts=None):
        if not isinstance(n, int) or n <= 0:
            raise ValueError("n must be a positive integer")
        rng = Random(seed)
        attempts = max_attempts if max_attempts is not None else max(10000, n * 1000)
        pools = [tuple(zip(*r.entries)) for r in self.ranges]
        result = []
        # Reject the ENTIRE independent draw. Sequentially renormalizing each
        # remaining range would bias earlier players' marginal probabilities.
        for _ in range(attempts):
            hands = tuple(rng.choices(c, weights=w)[0] for c, w in pools)
            if self.legal(hands):
                result.append(Deal(hands, 1 / n))
                if len(result) == n:
                    return tuple(result)
        raise RuntimeError("Rejection budget exhausted; ranges may be incompatible")


def generate_legal_multiway_matchups(ranges, board, mode="exact", samples=10000, seed=None):
    distribution = MultiwayDealDistribution(ranges, board)
    if mode == "exact":
        return distribution.exact()
    if mode in ("sample", "sampling"):
        return distribution.sample(samples, seed)
    raise ValueError("mode must be exact or sampling")
