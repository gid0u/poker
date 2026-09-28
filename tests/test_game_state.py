import unittest

from poker_evaluator.actions import Action, ActionType, Street
from poker_evaluator.cards import parse_card
from poker_evaluator.game_state import GameState, PlayerState


def make_river_state() -> GameState:
    board = tuple(parse_card(card) for card in ["Ks", "8h", "7d", "3c", "2s"])

    players = [
        PlayerState(
            player_id=0,
            stack=100,
            hole_cards=(
                parse_card("Kh"),
                parse_card("Qh"),
            ),
        ),
        PlayerState(
            player_id=1,
            stack=100,
            hole_cards=(
                parse_card("As"),
                parse_card("Jc"),
            ),
        ),
    ]

    return GameState(
        players=players,
        pot=100,
        acting_player_index=0,
        board=board,
        street=Street.RIVER,
    )


class TestGameState(unittest.TestCase):
    def test_initial_legal_actions(self) -> None:
        state = make_river_state()

        actions = state.legal_actions()

        self.assertIn(
            Action(ActionType.CHECK),
            actions,
        )
        self.assertIn(
            Action(ActionType.BET, amount=50),
            actions,
        )
        self.assertIn(
            Action(ActionType.ALL_IN, amount=100),
            actions,
        )

    def test_check_check_reaches_showdown(self) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        self.assertTrue(state.terminal)
        self.assertTrue(state.showdown)
        self.assertEqual(state.street, Street.SHOWDOWN)
        self.assertIsNone(state.winner_index)

    def test_bet_fold(self) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.BET, amount=50))

        self.assertEqual(state.pot, 150)
        self.assertEqual(state.players[0].stack, 50)
        self.assertEqual(state.acting_player_index, 1)

        state.apply_action(Action(ActionType.FOLD))

        self.assertTrue(state.terminal)
        self.assertFalse(state.showdown)
        self.assertEqual(state.winner_index, 0)

    def test_bet_call(self) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.BET, amount=50))
        state.apply_action(Action(ActionType.CALL, amount=50))

        self.assertTrue(state.terminal)
        self.assertTrue(state.showdown)
        self.assertEqual(state.pot, 200)
        self.assertEqual(state.players[0].stack, 50)
        self.assertEqual(state.players[1].stack, 50)

    def test_illegal_check_facing_bet(self) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.BET, amount=50))

        with self.assertRaises(ValueError):
            state.apply_action(Action(ActionType.CHECK))

    def test_clone_is_independent(self) -> None:
        state = make_river_state()
        cloned = state.clone()

        cloned.apply_action(Action(ActionType.BET, amount=50))

        self.assertEqual(state.pot, 100)
        self.assertEqual(cloned.pot, 150)

    def test_history_string(self) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.BET, amount=50))

        self.assertEqual(
            state.history_string(),
            "P0:check/P1:bet(50)",
        )


if __name__ == "__main__":
    unittest.main()
