from poker_evaluator.cards import Card
from poker_evaluator.evaluate5 import HandValue
from poker_evaluator.evaluate7 import best_five_hands
from poker_evaluator.rank_table import rank_from_value


def evaluate_holdem(
    hole_cards: list[Card],
    board_cards: list[Card],
) -> tuple[HandValue, int, list[tuple[Card, ...]]]:
    """ホールカード2枚とボード5枚から最強の5枚役を評価する。"""

    if len(hole_cards) != 2:
        raise ValueError(f"ホールカードは2枚必要です。入力枚数: {len(hole_cards)}")

    if len(board_cards) != 5:
        raise ValueError(f"ボードカードは5枚必要です。入力枚数: {len(board_cards)}")

    all_cards = hole_cards + board_cards

    if len(set(all_cards)) != 7:
        raise ValueError("ホールカードとボードに重複カードがあります")

    value, best_hands = best_five_hands(all_cards)
    rank = rank_from_value(value)

    return value, rank, best_hands
