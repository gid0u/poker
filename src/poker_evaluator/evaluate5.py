from collections import Counter

from poker_evaluator.cards import Card


def straight_high(ranks: list[int]) -> int | None:
    """5枚のランクがストレートなら最高ランクを返す。"""

    unique_ranks = sorted(set(ranks), reverse=True)

    if len(unique_ranks) != 5:
        return None

    # A-2-3-4-5は5ハイ・ストレートとして扱う
    if unique_ranks == [14, 5, 4, 3, 2]:
        return 5

    if unique_ranks[0] - unique_ranks[-1] == 4:
        return unique_ranks[0]

    return None


def validate_five_cards(cards: list[Card]) -> None:
    """5枚役として評価可能なカード集合か確認する。"""

    if len(cards) != 5:
        raise ValueError(f"5枚のカードが必要です。入力枚数: {len(cards)}")

    if len(set(cards)) != 5:
        raise ValueError("同一カードが重複しています")


def count_ranks(cards: list[Card]) -> Counter[int]:
    """5枚のカードについて、ランクごとの枚数を数える。"""

    validate_five_cards(cards)

    return Counter(card.rank for card in cards)


def is_flush(cards: list[Card]) -> bool:
    """5枚すべてが同じスートならTrueを返す。"""

    validate_five_cards(cards)

    suits = {card.suit for card in cards}

    return len(suits) == 1


def rank_groups(cards: list[Card]) -> list[tuple[int, int]]:
    """ランクを（枚数, ランク）の順で並べて返す。"""

    counts = count_ranks(cards)

    return sorted(
        ((count, rank) for rank, count in counts.items()),
        reverse=True,
    )


HandValue = tuple[int, ...]


def evaluate5(cards: list[Card]) -> HandValue:
    """5枚のカードを評価し、比較可能なタプルを返す。"""

    validate_five_cards(cards)

    ranks = sorted((card.rank for card in cards), reverse=True)
    groups = rank_groups(cards)
    straight = straight_high(ranks)
    flush = is_flush(cards)

    # 8: ストレートフラッシュ
    if straight is not None and flush:
        return (8, straight)

    # 7: フォーカード
    if groups[0][0] == 4:
        four_rank = groups[0][1]
        kicker = groups[1][1]
        return (7, four_rank, kicker)

    # 6: フルハウス
    if groups[0][0] == 3 and groups[1][0] == 2:
        trips_rank = groups[0][1]
        pair_rank = groups[1][1]
        return (6, trips_rank, pair_rank)

    # 5: フラッシュ
    if flush:
        return (5, *ranks)

    # 4: ストレート
    if straight is not None:
        return (4, straight)

    # 3: スリーカード
    if groups[0][0] == 3:
        trips_rank = groups[0][1]
        kickers = sorted(
            (rank for count, rank in groups if count == 1),
            reverse=True,
        )
        return (3, trips_rank, *kickers)

    # 2: ツーペア
    if groups[0][0] == 2 and groups[1][0] == 2:
        high_pair = max(groups[0][1], groups[1][1])
        low_pair = min(groups[0][1], groups[1][1])
        kicker = groups[2][1]
        return (2, high_pair, low_pair, kicker)

    # 1: ワンペア
    if groups[0][0] == 2:
        pair_rank = groups[0][1]
        kickers = sorted(
            (rank for count, rank in groups if count == 1),
            reverse=True,
        )
        return (1, pair_rank, *kickers)

    # 0: ハイカード
    return (0, *ranks)
