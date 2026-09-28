import unittest

from poker_evaluator.actions import (
    Action,
    ActionType,
    Street,
)
from poker_evaluator.cards import parse_card
from poker_evaluator.game_state import (
    GameState,
    PlayerState,
)
from poker_evaluator.utility import terminal_utility


def make_river_state(
    player_0_cards: tuple[str, str] = ("Kh", "Qh"),
    player_1_cards: tuple[str, str] = ("As", "Jc"),
    board_cards: tuple[str, str, str, str, str] = (
        "Ks",
        "8h",
        "7d",
        "3c",
        "2s",
    ),
    player_0_stack: int = 100,
    player_1_stack: int = 100,
    pot: int = 100,
) -> GameState:
    """
    テスト用のリバー状態を作成する。

    デフォルトでは、
    P0のKワンペアがP1のAハイに勝つ。
    """

    return GameState(
        players=[
            PlayerState(
                player_id=0,
                stack=player_0_stack,
                hole_cards=(
                    parse_card(player_0_cards[0]),
                    parse_card(player_0_cards[1]),
                ),
            ),
            PlayerState(
                player_id=1,
                stack=player_1_stack,
                hole_cards=(
                    parse_card(player_1_cards[0]),
                    parse_card(player_1_cards[1]),
                ),
            ),
        ],
        pot=pot,
        acting_player_index=0,
        board=tuple(parse_card(card) for card in board_cards),
        street=Street.RIVER,
    )


class TestTerminalUtility(unittest.TestCase):
    def assert_zero_sum(
        self,
        state: GameState,
    ) -> None:
        """
        P0とP1の利得の合計が0であることを確認する。
        """

        utility_0 = terminal_utility(state, 0)
        utility_1 = terminal_utility(state, 1)

        self.assertAlmostEqual(
            utility_0 + utility_1,
            0.0,
        )

    def test_rejects_invalid_player_index(self) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        with self.assertRaises(ValueError):
            terminal_utility(state, -1)

        with self.assertRaises(ValueError):
            terminal_utility(state, 2)

    def test_rejects_non_terminal_state(self) -> None:
        state = make_river_state()

        with self.assertRaises(ValueError):
            terminal_utility(state, 0)

    def test_check_check_showdown_win(self) -> None:
        """
        初期ポット100を基準にする。

        P0が勝つので、
        P0は基準持分50から100を受け取り、+50。
        P1は何も受け取らず、-50。
        """

        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        self.assertTrue(state.terminal)
        self.assertTrue(state.showdown)

        self.assertEqual(
            terminal_utility(state, 0),
            50.0,
        )
        self.assertEqual(
            terminal_utility(state, 1),
            -50.0,
        )

        self.assert_zero_sum(state)

    def test_bet_fold(self) -> None:
        """
        初期ポット100。

        P0が50ベットし、P1がフォールドする。

        P0:
            150受取 - 50追加投入 - 50基準持分
            = +50

        P1:
            0受取 - 0追加投入 - 50基準持分
            = -50
        """

        state = make_river_state()

        state.apply_action(
            Action(
                ActionType.BET,
                amount=50,
            )
        )
        state.apply_action(Action(ActionType.FOLD))

        self.assertTrue(state.terminal)
        self.assertFalse(state.showdown)
        self.assertEqual(state.winner_index, 0)

        self.assertEqual(
            terminal_utility(state, 0),
            50.0,
        )
        self.assertEqual(
            terminal_utility(state, 1),
            -50.0,
        )

        self.assert_zero_sum(state)

    def test_bet_call_showdown_win(self) -> None:
        """
        初期ポット100。

        P0が50ベットし、P1が50コールする。
        P0がショーダウンで勝つ。

        P0:
            200受取 - 50追加投入 - 50基準持分
            = +100

        P1:
            0受取 - 50追加投入 - 50基準持分
            = -100
        """

        state = make_river_state()

        state.apply_action(
            Action(
                ActionType.BET,
                amount=50,
            )
        )
        state.apply_action(
            Action(
                ActionType.CALL,
                amount=50,
            )
        )

        self.assertTrue(state.terminal)
        self.assertTrue(state.showdown)
        self.assertEqual(state.pot, 200)

        self.assertEqual(
            terminal_utility(state, 0),
            100.0,
        )
        self.assertEqual(
            terminal_utility(state, 1),
            -100.0,
        )

        self.assert_zero_sum(state)

    def test_player_1_wins_showdown(self) -> None:
        """
        P1にKワンペアを与え、P0をAハイにする。
        """

        state = make_river_state(
            player_0_cards=("As", "Jc"),
            player_1_cards=("Kh", "Qh"),
        )

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        self.assertEqual(
            terminal_utility(state, 0),
            -50.0,
        )
        self.assertEqual(
            terminal_utility(state, 1),
            50.0,
        )

        self.assert_zero_sum(state)

    def test_check_check_tie(self) -> None:
        """
        両者が同じAハイストレートを作る。

        初期ポット100を50ずつ分けるため、
        両者の純利得は0。
        """

        state = make_river_state(
            player_0_cards=("Ah", "Qh"),
            player_1_cards=("Ad", "Qc"),
            board_cards=(
                "Ks",
                "Jd",
                "Tc",
                "3c",
                "2s",
            ),
        )

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        self.assertEqual(
            terminal_utility(state, 0),
            0.0,
        )
        self.assertEqual(
            terminal_utility(state, 1),
            0.0,
        )

        self.assert_zero_sum(state)

    def test_bet_call_tie(self) -> None:
        """
        50ベット・50コール後に引き分け。

        両者は100ずつ受け取るが、
        追加投入50と基準持分50を差し引くため0。
        """

        state = make_river_state(
            player_0_cards=("Ah", "Qh"),
            player_1_cards=("Ad", "Qc"),
            board_cards=(
                "Ks",
                "Jd",
                "Tc",
                "3c",
                "2s",
            ),
        )

        state.apply_action(
            Action(
                ActionType.BET,
                amount=50,
            )
        )
        state.apply_action(
            Action(
                ActionType.CALL,
                amount=50,
            )
        )

        self.assertEqual(
            terminal_utility(state, 0),
            0.0,
        )
        self.assertEqual(
            terminal_utility(state, 1),
            0.0,
        )

        self.assert_zero_sum(state)

    def test_all_in_call_showdown(self) -> None:
        """
        両者が100ずつ投入してP0が勝つ。

        最終ポット300。

        P0:
            300 - 100 - 50 = +150

        P1:
            0 - 100 - 50 = -150
        """

        state = make_river_state()

        state.apply_action(
            Action(
                ActionType.ALL_IN,
                amount=100,
            )
        )
        state.apply_action(
            Action(
                ActionType.CALL,
                amount=100,
            )
        )

        self.assertEqual(state.pot, 300)

        self.assertEqual(
            terminal_utility(state, 0),
            150.0,
        )
        self.assertEqual(
            terminal_utility(state, 1),
            -150.0,
        )

        self.assert_zero_sum(state)

    def test_short_stack_call_refunds_uncalled_chips(self) -> None:
        """
        P0が100をオールインし、
        P1は残り60だけコールする。

        P0の超過40は未コール分なので返却される。

        争われるポット:
            初期100 + 60 + 60 = 220

        P0の受取:
            争われる220 + 返却40 = 260

        P0の利得:
            260 - 100 - 50 = +110

        P1の利得:
            0 - 60 - 50 = -110
        """

        state = make_river_state(
            player_0_stack=100,
            player_1_stack=60,
        )

        state.apply_action(
            Action(
                ActionType.ALL_IN,
                amount=100,
            )
        )

        self.assertIn(
            Action(
                ActionType.CALL,
                amount=60,
            ),
            state.legal_actions(),
        )

        state.apply_action(
            Action(
                ActionType.CALL,
                amount=60,
            )
        )

        self.assertEqual(state.pot, 260)

        self.assertEqual(
            terminal_utility(state, 0),
            110.0,
        )
        self.assertEqual(
            terminal_utility(state, 1),
            -110.0,
        )

        self.assert_zero_sum(state)

    def test_showdown_requires_hole_cards(self) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        state.players[0].hole_cards = None

        with self.assertRaises(ValueError):
            terminal_utility(state, 0)


if __name__ == "__main__":
    unittest.main()
