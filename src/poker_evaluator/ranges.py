import re
from itertools import combinations

from poker_evaluator.cards import Card, RANKS, SUITS


HoleCombo = tuple[Card, Card]

RANK_SYMBOLS = "23456789TJQKA"

RANGE_TOKEN_PATTERN = re.compile(r"^([2-9TJQKA])([2-9TJQKA])([SO])?(\+)?$")


def normalize_hole_combo(
    card1: Card,
    card2: Card,
) -> HoleCombo:
    """2枚のカードを一定の順序に並べて返す。"""

    if card1 == card2:
        raise ValueError("同一カードを2枚組にはできません")

    ordered = sorted(
        (card1, card2),
        reverse=True,
    )

    return ordered[0], ordered[1]


def expand_pair(rank_symbol: str) -> set[HoleCombo]:
    """ポケットペアを6通りの具体的なカードへ展開する。"""

    rank = RANKS[rank_symbol]
    suits = list(SUITS.values())

    return {
        normalize_hole_combo(
            Card(rank=rank, suit=suit1),
            Card(rank=rank, suit=suit2),
        )
        for suit1, suit2 in combinations(suits, 2)
    }


def expand_non_pair(
    high_rank_symbol: str,
    low_rank_symbol: str,
    suitedness: str | None,
) -> set[HoleCombo]:
    """非ペアをスート別の具体的なカードへ展開する。"""

    high_rank = RANKS[high_rank_symbol]
    low_rank = RANKS[low_rank_symbol]
    suits = list(SUITS.values())

    combos: set[HoleCombo] = set()

    for high_suit in suits:
        for low_suit in suits:
            is_suited = high_suit == low_suit

            if suitedness == "S" and not is_suited:
                continue

            if suitedness == "O" and is_suited:
                continue

            combos.add(
                normalize_hole_combo(
                    Card(
                        rank=high_rank,
                        suit=high_suit,
                    ),
                    Card(
                        rank=low_rank,
                        suit=low_suit,
                    ),
                )
            )

    return combos


def expand_range_token(token: str) -> tuple[HoleCombo, ...]:
    """単一のレンジ表記を具体的な2枚組へ展開する。"""

    normalized_token = token.strip().upper()

    match = RANGE_TOKEN_PATTERN.fullmatch(normalized_token)

    if match is None:
        raise ValueError(f"不正なレンジ表記です: {token!r}")

    first_symbol = match.group(1)
    second_symbol = match.group(2)
    suitedness = match.group(3)
    has_plus = match.group(4) is not None

    first_rank = RANKS[first_symbol]
    second_rank = RANKS[second_symbol]

    if first_rank < second_rank:
        raise ValueError(f"レンジ表記は高いランクを先にしてください: {token!r}")

    is_pair = first_rank == second_rank

    if is_pair:
        if suitedness is not None:
            raise ValueError(f"ポケットペアにsまたはoは指定できません: {token!r}")

        if not has_plus:
            combos = expand_pair(first_symbol)
            return tuple(sorted(combos, reverse=True))

        start_index = RANK_SYMBOLS.index(first_symbol)

        combos: set[HoleCombo] = set()

        for rank_symbol in RANK_SYMBOLS[start_index:]:
            combos.update(expand_pair(rank_symbol))

        return tuple(sorted(combos, reverse=True))

    if has_plus:
        raise ValueError(f"非ペアへの+指定はまだ対応していません: {token!r}")

    combos = expand_non_pair(
        high_rank_symbol=first_symbol,
        low_rank_symbol=second_symbol,
        suitedness=suitedness,
    )

    return tuple(sorted(combos, reverse=True))


def parse_range(text: str) -> tuple[HoleCombo, ...]:
    """複数のレンジ表記を具体的な2枚組へ展開する。"""

    tokens = [token for token in re.split(r"[\s,]+", text.strip()) if token]

    if not tokens:
        raise ValueError("レンジ表記が空です")

    combos: set[HoleCombo] = set()

    for token in tokens:
        combos.update(expand_range_token(token))

    return tuple(sorted(combos, reverse=True))


def filter_blocked_combos(
    combos: tuple[HoleCombo, ...],
    known_cards: list[Card],
) -> tuple[HoleCombo, ...]:
    """Heroやボードと重複する組合せを除外する。"""

    if len(set(known_cards)) != len(known_cards):
        raise ValueError("既知のカードに重複があります")

    known_set = set(known_cards)

    return tuple(
        combo
        for combo in combos
        if combo[0] not in known_set and combo[1] not in known_set
    )
