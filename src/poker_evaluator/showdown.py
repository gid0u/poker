from dataclasses import dataclass
from enum import Enum

from poker_evaluator.cards import Card
from poker_evaluator.evaluate5 import HandValue
from poker_evaluator.holdem import evaluate_holdem


class ShowdownResult(Enum):
    """2人のショーダウン結果。"""

    PLAYER1_WIN = "player1_win"
    PLAYER2_WIN = "player2_win"
    TIE = "tie"


@dataclass(frozen=True)
class MultiwayShowdownResult:
    """複数人ショーダウンの評価結果。"""

    hand_values: tuple[HandValue, ...]
    winner_indices: tuple[int, ...]

    @property
    def is_tie(self) -> bool:
        """勝者が複数いる場合にTrueを返す。"""

        return len(self.winner_indices) > 1


def compare_multiway_holdem(
    player_holes: list[list[Card]],
    board_cards: list[Card],
) -> MultiwayShowdownResult:
    """複数人のホールカードを共通ボード上で比較する。"""

    if len(player_holes) < 2:
        raise ValueError(f"プレイヤーは2人以上必要です。入力人数: {len(player_holes)}")

    for player_number, hole_cards in enumerate(
        player_holes,
        start=1,
    ):
        if len(hole_cards) != 2:
            raise ValueError(
                f"プレイヤー{player_number}のホールカードは"
                f"2枚必要です。入力枚数: {len(hole_cards)}"
            )

    if len(board_cards) != 5:
        raise ValueError(f"ボードカードは5枚必要です。入力枚数: {len(board_cards)}")

    all_cards = [
        card for hole_cards in player_holes for card in hole_cards
    ] + board_cards

    if len(set(all_cards)) != len(all_cards):
        raise ValueError("プレイヤー間またはボードに重複カードがあります")

    hand_values = tuple(
        evaluate_holdem(hole_cards, board_cards)[0] for hole_cards in player_holes
    )

    best_value = max(hand_values)

    winner_indices = tuple(
        index for index, value in enumerate(hand_values) if value == best_value
    )

    return MultiwayShowdownResult(
        hand_values=hand_values,
        winner_indices=winner_indices,
    )


def compare_holdem(
    player1_hole: list[Card],
    player2_hole: list[Card],
    board_cards: list[Card],
) -> ShowdownResult:
    """2人のホールカードを共通ボード上で比較する。"""

    result = compare_multiway_holdem(
        [player1_hole, player2_hole],
        board_cards,
    )

    if result.winner_indices == (0,):
        return ShowdownResult.PLAYER1_WIN

    if result.winner_indices == (1,):
        return ShowdownResult.PLAYER2_WIN

    return ShowdownResult.TIE
