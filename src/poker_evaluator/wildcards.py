"""Exact conditional distributions of seven-card sets, not joker best-casing."""
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations, permutations
from math import isfinite, prod, fsum, factorial
from functools import lru_cache
import re

from .cards import Card
from .rank_table import rank_seven_cards, load_rank_table
from .seven_card_dictionary import CATEGORY_NAMES, card_id, HAND_COUNT

RANKS = "23456789TJQKA"
SUITS = "SCHD"
VARIABLE_SUITS = "OPQR"
TOKEN = re.compile(r"^(?:(X)([1-9][0-9]*)?|([2-9TJQKA]))([SCHDOPQR])?$", re.I)
HOLDEM_GROUPS = (2, 3, 1, 1)


def normalize_groups(group_sizes):
    sizes = (7,) if group_sizes is None else tuple(group_sizes)
    if not sizes or any(type(n) is not int or n <= 0 for n in sizes) or sum(sizes) != 7:
        raise ValueError("Group sizes must be positive integers summing to seven")
    return sizes


class ExpansionLimitError(ValueError):
    """Exact enumeration budget exceeded; never return a partial average."""


@dataclass(frozen=True)
class Slot:
    rank: int | None
    suit: str | None
    wildcard: int | None = None


@dataclass(frozen=True)
class WildcardPattern:
    slots: tuple[Slot, ...]
    normalized: str

    @classmethod
    def parse(cls, text):
        if not isinstance(text, str):
            raise ValueError("Pattern must be a string")
        tokens = text.replace(",", " ").split()
        if len(tokens) != 7:
            raise ValueError("Specify exactly seven cards, including wildcards")
        slots, normalized, labels = [], [], set()
        ordinal = 0
        for token in tokens:
            match = TOKEN.fullmatch(token)
            if match is None:
                raise ValueError(f"Invalid wildcard card: {token}")
            unknown, label, rank, suit = match.groups()
            suit = suit.upper() if suit else None
            if unknown:
                if label is not None and label in labels:
                    raise ValueError("One named unknown card cannot occupy two positions")
                if label:
                    labels.add(label)
                ordinal += 1
                slots.append(Slot(None, suit, ordinal))
                normalized.append(f"X{ordinal}{suit or ''}")
            else:
                if suit is None:
                    raise ValueError("Known ranks need a physical or variable suit (e.g. QS or QO)")
                rank = rank.upper()
                slots.append(Slot(RANKS.index(rank)+2, suit))
                normalized.append(rank+suit)
        return cls(tuple(slots), " ".join(normalized))

    def outcomes(self, *, dead_cards=(), card_weights=None, hand_weight=None, max_candidates=1000000,
                 group_sizes=None):
        """Unique unordered physical sets. Product card weights x optional hand mass.

        The enumeration budget counts complete assignments before deduplication.
        Equivalent unknown slots are ordered during enumeration to avoid factorial
        duplication. Distinct suit assignments may still yield the same set.
        """
        if type(max_candidates) is not int or max_candidates <= 0:
            raise ValueError("Positive max_candidates required")
        sizes = normalize_groups(group_sizes)
        slot_groups = tuple(i for i, size in enumerate(sizes) for _ in range(size))
        dead = frozenset(card_id(c) for c in dead_cards)
        weights = {}
        for key, value in (card_weights or {}).items():
            if not isfinite(value) or value < 0:
                raise ValueError("Card weights must be finite and nonnegative")
            identifier = card_id(key)
            if identifier in weights:
                raise ValueError("Duplicate card weight after normalization")
            weights[identifier] = float(value)
        fixed = [4*(s.rank-2)+SUITS.index(s.suit) for s in self.slots
                 if s.rank is not None and s.suit in SUITS]
        if len(set(fixed)) != len(fixed) or set(fixed) & dead:
            raise ValueError("Fixed cards overlap each other or dead cards")
        fixed_suits = {SUITS.index(s.suit) for s in self.slots if s.suit is not None and s.suit in SUITS}
        fixed_suits.update(c % 4 for c in dead)
        variables = tuple(dict.fromkeys(s.suit for s in self.slots if s.suit is not None and s.suit in VARIABLE_SUITS))
        available = [s for s in range(4) if s not in fixed_suits]
        if len(variables) > len(available):
            raise ValueError("Not enough unused physical suits for distinct suit variables")
        seen = set()
        attempts = 0
        for assigned in permutations(available, len(variables)):
            mapping = dict(zip(variables, assigned))
            groups = Counter()
            for slot, group_id in zip(self.slots, slot_groups):
                suit = (SUITS.index(slot.suit) if slot.suit in SUITS else mapping[slot.suit]) if slot.suit else None
                pool = tuple(i for i in range(52) if i not in dead
                             and (slot.rank is None or i//4+2 == slot.rank)
                             and (suit is None or i%4 == suit))
                groups[(group_id, pool)] += 1
            # Resolve the tightest pools first. Identical pools choose combinations.
            grouped = sorted(groups.items(), key=lambda pair: len(pair[0][1]))

            def visit(position, used, parts):
                nonlocal attempts
                if position == len(grouped):
                    attempts += 1
                    if attempts > max_candidates:
                        raise ExpansionLimitError("Exact expansion exceeds max_candidates; no partial result returned")
                    key = tuple(tuple(sorted(part)) for part in parts)
                    if key in seen:
                        return
                    seen.add(key)
                    ids = tuple(i for part in key for i in part)
                    cards = tuple(Card(i//4+2, i%4) for i in ids)
                    mass = prod(weights.get(i, 1.0) for i in ids)
                    if hand_weight is not None:
                        factor = hand_weight(cards)
                        if not isfinite(factor) or factor < 0:
                            raise ValueError("Hand weights must be finite and nonnegative")
                        mass *= factor
                    if not isfinite(mass):
                        raise ValueError("Combined weight overflow")
                    if mass:
                        yield cards, mass
                    return
                (group_id, pool), count = grouped[position]
                allowed = [i for i in pool if i not in used]
                for selected in combinations(allowed, count):
                    next_parts = list(parts)
                    next_parts[group_id] = parts[group_id] + selected
                    yield from visit(position+1, used | frozenset(selected), tuple(next_parts))

            yield from visit(0, frozenset(), ((),) * len(sizes))


@dataclass(frozen=True)
class WildcardEvaluation:
    normalized: str
    legal_hands: int
    total_weight: float
    mean_rank: float
    mean_strength: float
    best_rank: int
    worst_rank: int
    rank_probabilities: dict[int, float]
    category_probabilities: dict[str, float]
    conditions: dict = field(default_factory=dict)
    method: str = "exact"

    def expectation(self, value_by_rank):
        """Expected value of any caller-provided scalar rank utility."""
        return fsum(p*value_by_rank(rank) for rank, p in self.rank_probabilities.items())


def _summary(pattern, masses, count, conditions):
    total = fsum(masses.values())
    if not isfinite(total) or total <= 0:
        raise ValueError("No legal hand with positive finite weight")
    probabilities = {rank: mass/total for rank, mass in sorted(masses.items())}
    categories = [0.0] * 9
    classes = sorted(load_rank_table(), reverse=True)
    for rank, probability in probabilities.items():
        categories[classes[rank-1][0]] += probability
    mean = fsum(rank*p for rank, p in probabilities.items())
    return WildcardEvaluation(pattern.normalized, count, total, mean, 7463-mean,
        min(probabilities), max(probabilities), probabilities, dict(zip(CATEGORY_NAMES, categories)), conditions)


def evaluate_wildcards(pattern, *, ranker=None, dead_cards=(), card_weights=None,
                       hand_weight=None, max_candidates=1000000, group_sizes=None):
    """Exact weighted mean over unique legal sets. Smaller mean_rank is stronger.

    ranker may be an open SevenCardRankDictionary or callable(cards)->1..7462.
    Without one, the original 21-subset evaluator is used. No sampling occurs.
    """
    pattern = WildcardPattern.parse(pattern) if isinstance(pattern, str) else pattern
    if not isinstance(pattern, WildcardPattern):
        raise ValueError("Expected a seven-card wildcard pattern")
    if type(max_candidates) is not int or max_candidates <= 0:
        raise ValueError("Positive max_candidates required")
    sizes = normalize_groups(group_sizes)
    dead_cards = tuple(dead_cards)
    conditions = dict(dead_card_ids=sorted({card_id(c) for c in dead_cards}),
        card_weights={str(card_id(c)): w for c, w in (card_weights or {}).items()},
        custom_hand_weight=hand_weight is not None, group_sizes=list(sizes),
        measure="unique physical sets within each ordered group")
    # All 7 unknowns have a direct exact histogram over the already built table.
    from .seven_card_dictionary import SevenCardRankDictionary, DATA_FILENAME
    if (isinstance(ranker, SevenCardRankDictionary) and not dead_cards and not card_weights
            and hand_weight is None and all(s.rank is None and s.suit is None for s in pattern.slots)):
        from array import array
        import sys
        masses = Counter()
        with (ranker.directory / DATA_FILENAME).open("rb") as stream:
            for data in iter(lambda: stream.read(2*1000000), b""):
                values = array("H")
                values.frombytes(data)
                if sys.byteorder != "little":
                    values.byteswap()
                masses.update(values)
        if any(not 1 <= r <= 7462 for r in masses) or sum(masses.values()) != HAND_COUNT:
            raise ValueError("Corrupt dictionary")
        multiplicity = factorial(7) // prod(factorial(n) for n in sizes)
        if multiplicity != 1:
            masses = Counter({r: n*multiplicity for r, n in masses.items()})
        return _summary(pattern, masses, HAND_COUNT*multiplicity, conditions)
    function = ranker.__getitem__ if isinstance(ranker, SevenCardRankDictionary) else ranker or rank_seven_cards
    # Strength depends on the final seven-card set, not its reveal partition.
    # Keep role-specific outcome weights while avoiding repeated rank evaluation.
    cached_rank = lru_cache(maxsize=100000)(function)
    masses = Counter()
    count = 0
    for cards, mass in pattern.outcomes(dead_cards=dead_cards, card_weights=card_weights,
                                        hand_weight=hand_weight, max_candidates=max_candidates,
                                        group_sizes=sizes):
        rank = cached_rank(tuple(sorted(cards)))
        if type(rank) is not int or not 1 <= rank <= 7462:
            raise ValueError("Rank evaluator must return an integer in [1,7462]")
        masses[rank] += mass
        count += 1
    return _summary(pattern, masses, count, conditions)


def evaluate_holdem_wildcards(pattern, **options):
    """Input order: hole[2], flop[3], turn[1], river[1]."""
    return evaluate_wildcards(pattern, group_sizes=HOLDEM_GROUPS, **options)
