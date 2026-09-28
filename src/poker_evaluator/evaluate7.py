from itertools import combinations

from poker_evaluator.cards import Card
from poker_evaluator.evaluate5 import HandValue, evaluate5


def validate_seven_cards(cards: list[Card]) -> None:
    """7枚役として評価可能なカード集合か確認する。"""

    if len(cards) != 7:
        raise ValueError(f"7枚のカードが必要です。入力枚数: {len(cards)}")

    if len(set(cards)) != 7:
        raise ValueError("同一カードが重複しています")


def evaluate7(cards: list[Card]) -> HandValue:
    """7枚から選べる全21通りの5枚役を評価し、最強値を返す。"""

    validate_seven_cards(cards)

    return max(evaluate5(list(hand)) for hand in combinations(cards, 5))


def best_five_hands(
    cards: list[Card],
) -> tuple[HandValue, list[tuple[Card, ...]]]:
    """7枚から最強の5枚役と、それを作る全5枚組を返す。"""

    validate_seven_cards(cards)

    candidates = [(evaluate5(list(hand)), hand) for hand in combinations(cards, 5)]

    best_value = max(value for value, _ in candidates)

    best_hands = [hand for value, hand in candidates if value == best_value]

    return best_value, best_hands
