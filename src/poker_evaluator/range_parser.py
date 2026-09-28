from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from .cards import Card


RANK_ORDER: tuple[str, ...] = (
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "T",
    "J",
    "Q",
    "K",
    "A",
)

RANK_TO_VALUE: dict[str, int] = {
    rank: index + 2 for index, rank in enumerate(RANK_ORDER)
}

VALUE_TO_RANK: dict[int, str] = {value: rank for rank, value in RANK_TO_VALUE.items()}

SUITS: tuple[int, ...] = (0, 1, 2, 3)


@dataclass(frozen=True)
class HandCombo:
    first: Card
    second: Card

    def __post_init__(self) -> None:
        if self.first == self.second:
            raise ValueError("A hand combo cannot contain the same card twice.")

    @property
    def cards(self) -> tuple[Card, Card]:
        return self.first, self.second

    def contains(
        self,
        card: Card,
    ) -> bool:
        return card == self.first or card == self.second

    def overlaps(
        self,
        cards: Iterable[Card],
    ) -> bool:
        blocked = set(cards)

        return self.first in blocked or self.second in blocked

    def normalized(
        self,
    ) -> frozenset[Card]:
        return frozenset(
            (
                self.first,
                self.second,
            )
        )


def _normalize_rank(
    rank: str,
) -> str:
    normalized = rank.upper()

    if normalized not in RANK_TO_VALUE:
        raise ValueError(f"Invalid rank: {rank}")

    return normalized


def _make_card(
    rank: str,
    suit: int,
) -> Card:
    return Card(
        rank=RANK_TO_VALUE[rank],
        suit=suit,
    )


def generate_pair_combos(
    rank: str,
) -> tuple[HandCombo, ...]:
    rank = _normalize_rank(rank)

    cards = [_make_card(rank, suit) for suit in SUITS]

    return tuple(
        HandCombo(first, second)
        for first, second in combinations(
            cards,
            2,
        )
    )


def generate_suited_combos(
    high_rank: str,
    low_rank: str,
) -> tuple[HandCombo, ...]:
    high_rank = _normalize_rank(high_rank)
    low_rank = _normalize_rank(low_rank)

    if high_rank == low_rank:
        raise ValueError("Suited notation cannot be used for a pair.")

    return tuple(
        HandCombo(
            _make_card(high_rank, suit),
            _make_card(low_rank, suit),
        )
        for suit in SUITS
    )


def generate_offsuit_combos(
    high_rank: str,
    low_rank: str,
) -> tuple[HandCombo, ...]:
    high_rank = _normalize_rank(high_rank)
    low_rank = _normalize_rank(low_rank)

    if high_rank == low_rank:
        raise ValueError("Offsuit notation cannot be used for a pair.")

    combos: list[HandCombo] = []

    for high_suit in SUITS:
        for low_suit in SUITS:
            if high_suit == low_suit:
                continue

            combos.append(
                HandCombo(
                    _make_card(
                        high_rank,
                        high_suit,
                    ),
                    _make_card(
                        low_rank,
                        low_suit,
                    ),
                )
            )

    return tuple(combos)


def generate_any_suit_combos(
    high_rank: str,
    low_rank: str,
) -> tuple[HandCombo, ...]:
    return generate_suited_combos(
        high_rank,
        low_rank,
    ) + generate_offsuit_combos(
        high_rank,
        low_rank,
    )


def _validate_two_rank_token(
    token: str,
) -> tuple[str, str]:
    if len(token) != 2:
        raise ValueError(f"Expected a two-rank token: {token}")

    first = _normalize_rank(token[0])
    second = _normalize_rank(token[1])

    return first, second


def _rank_index(
    rank: str,
) -> int:
    return RANK_ORDER.index(rank)


def _expand_pair_plus(
    rank: str,
) -> tuple[str, ...]:
    start_index = _rank_index(rank)

    return tuple(current_rank * 2 for current_rank in RANK_ORDER[start_index:])


def _expand_non_pair_plus(
    high_rank: str,
    low_rank: str,
    suffix: str,
) -> tuple[str, ...]:
    high_index = _rank_index(high_rank)
    low_index = _rank_index(low_rank)

    if high_index <= low_index:
        raise ValueError("The first rank must be higher than the second rank.")

    expanded: list[str] = []

    for current_low_index in range(
        low_index,
        high_index,
    ):
        current_low = RANK_ORDER[current_low_index]

        expanded.append(f"{high_rank}{current_low}{suffix}")

    return tuple(expanded)


def expand_range_token(
    token: str,
) -> tuple[str, ...]:
    token = token.strip()

    if not token:
        raise ValueError("Range token cannot be empty.")

    has_plus = token.endswith("+")

    if has_plus:
        token = token[:-1]

    suffix = ""

    if token.endswith(
        (
            "s",
            "S",
            "o",
            "O",
        )
    ):
        suffix = token[-1].lower()
        token = token[:-1]

    first, second = _validate_two_rank_token(token)

    if first == second:
        if suffix:
            raise ValueError("Pair notation cannot use s or o.")

        if has_plus:
            return _expand_pair_plus(first)

        return (first + second,)

    first_index = _rank_index(first)
    second_index = _rank_index(second)

    if first_index < second_index:
        first, second = second, first

    if has_plus:
        return _expand_non_pair_plus(
            first,
            second,
            suffix,
        )

    return (f"{first}{second}{suffix}",)


def parse_exact_hand(
    notation: str,
) -> tuple[HandCombo, ...]:
    notation = notation.strip()

    suffix = ""

    if notation.endswith(
        (
            "s",
            "S",
            "o",
            "O",
        )
    ):
        suffix = notation[-1].lower()
        notation = notation[:-1]

    first, second = _validate_two_rank_token(notation)

    first_index = _rank_index(first)
    second_index = _rank_index(second)

    if first_index < second_index:
        first, second = second, first

    if first == second:
        if suffix:
            raise ValueError("Pair notation cannot use s or o.")

        return generate_pair_combos(first)

    if suffix == "s":
        return generate_suited_combos(
            first,
            second,
        )

    if suffix == "o":
        return generate_offsuit_combos(
            first,
            second,
        )

    return generate_any_suit_combos(
        first,
        second,
    )


def parse_range(
    range_text: str,
) -> tuple[HandCombo, ...]:
    if not isinstance(range_text, str):
        raise TypeError("Range must be provided as a string.")

    normalized_text = range_text.replace(
        "\n",
        ",",
    )

    tokens = [token.strip() for token in normalized_text.split(",") if token.strip()]

    if not tokens:
        raise ValueError("Range cannot be empty.")

    combos: list[HandCombo] = []
    seen: set[frozenset[Card]] = set()

    for token in tokens:
        expanded_tokens = expand_range_token(token)

        for expanded_token in expanded_tokens:
            for combo in parse_exact_hand(expanded_token):
                normalized_combo = combo.normalized()

                if normalized_combo in seen:
                    continue

                seen.add(normalized_combo)

                combos.append(combo)

    return tuple(combos)


def remove_blocked_combos(
    combos: Iterable[HandCombo],
    blocked_cards: Iterable[Card],
) -> tuple[HandCombo, ...]:
    blocked = set(blocked_cards)

    return tuple(combo for combo in combos if not combo.overlaps(blocked))
