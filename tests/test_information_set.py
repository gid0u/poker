import unittest

from poker_evaluator.actions import (
    Action,
    ActionType,
)
from poker_evaluator.cards import parse_card
from poker_evaluator.information_set import (
    InformationSet,
    InformationSetKey,
    _format_card,
    make_information_set,
    make_information_set_key,
)
from tests.test_game_tree import (
    make_river_state,
)


class TestCardFormatting(unittest.TestCase):
    def test_format_ace_of_spades(
        self,
    ) -> None:
        card = parse_card("As")

        self.assertEqual(
            _format_card(card),
            "As",
        )

    def test_format_king_of_hearts(
        self,
    ) -> None:
        card = parse_card("Kh")

        self.assertEqual(
            _format_card(card),
            "Kh",
        )

    def test_format_ten_of_diamonds(
        self,
    ) -> None:
        card = parse_card("Td")

        self.assertEqual(
            _format_card(card),
            "Td",
        )

    def test_format_number_card(
        self,
    ) -> None:
        card = parse_card("7c")

        self.assertEqual(
            _format_card(card),
            "7c",
        )

    def test_non_card_falls_back_to_str(
        self,
    ) -> None:
        self.assertEqual(
            _format_card("test"),
            "test",
        )


class TestInformationSetKey(unittest.TestCase):
    def test_key_uses_acting_player_by_default(
        self,
    ) -> None:
        state = make_river_state()

        key = make_information_set_key(state)

        self.assertEqual(
            key.player_index,
            0,
        )

        self.assertEqual(
            key.hole_cards,
            (
                "Kh",
                "Qh",
            ),
        )

    def test_key_contains_public_state(
        self,
    ) -> None:
        state = make_river_state()

        key = make_information_set_key(state)

        self.assertEqual(
            key.board,
            (
                "Ks",
                "8h",
                "7d",
                "3c",
                "2s",
            ),
        )

        self.assertEqual(
            key.action_history,
            tuple(),
        )

        self.assertEqual(
            key.pot,
            100,
        )

        self.assertEqual(
            key.stacks,
            (
                100,
                100,
            ),
        )

        self.assertEqual(
            key.committed,
            (
                0,
                0,
            ),
        )

        self.assertEqual(
            key.to_call,
            0,
        )

    def test_key_changes_after_action(
        self,
    ) -> None:
        state = make_river_state()

        root_key = make_information_set_key(state)

        state.apply_action(Action(ActionType.CHECK))

        child_key = make_information_set_key(state)

        self.assertNotEqual(
            root_key,
            child_key,
        )

        self.assertEqual(
            child_key.player_index,
            1,
        )

        self.assertEqual(
            child_key.action_history,
            ("check",),
        )

    def test_key_after_bet_contains_call_amount(
        self,
    ) -> None:
        state = make_river_state()

        state.apply_action(
            Action(
                ActionType.BET,
                amount=50,
            )
        )

        key = make_information_set_key(state)

        self.assertEqual(
            key.player_index,
            1,
        )

        self.assertEqual(
            key.action_history,
            ("bet(50)",),
        )

        self.assertEqual(
            key.pot,
            150,
        )

        self.assertEqual(
            key.stacks,
            (
                50,
                100,
            ),
        )

        self.assertEqual(
            key.committed,
            (
                50,
                0,
            ),
        )

        self.assertEqual(
            key.to_call,
            50,
        )

    def test_explicit_player_index(
        self,
    ) -> None:
        state = make_river_state()

        key = make_information_set_key(
            state,
            player_index=1,
        )

        self.assertEqual(
            key.player_index,
            1,
        )

        self.assertEqual(
            key.hole_cards,
            (
                "As",
                "Jc",
            ),
        )

    def test_invalid_player_index_rejected(
        self,
    ) -> None:
        state = make_river_state()

        with self.assertRaises(ValueError):
            make_information_set_key(
                state,
                player_index=-1,
            )

        with self.assertRaises(ValueError):
            make_information_set_key(
                state,
                player_index=2,
            )

    def test_opponent_hole_cards_do_not_affect_key(
        self,
    ) -> None:
        state_a = make_river_state()
        state_b = make_river_state()

        state_b.players[1].hole_cards = (
            parse_card("2h"),
            parse_card("2c"),
        )

        key_a = make_information_set_key(
            state_a,
            player_index=0,
        )

        key_b = make_information_set_key(
            state_b,
            player_index=0,
        )

        self.assertEqual(
            key_a,
            key_b,
        )

    def test_own_hole_cards_affect_key(
        self,
    ) -> None:
        state_a = make_river_state()
        state_b = make_river_state()

        state_b.players[0].hole_cards = (
            parse_card("Ah"),
            parse_card("Ad"),
        )

        key_a = make_information_set_key(
            state_a,
            player_index=0,
        )

        key_b = make_information_set_key(
            state_b,
            player_index=0,
        )

        self.assertNotEqual(
            key_a,
            key_b,
        )

    def test_key_is_hashable(
        self,
    ) -> None:
        state = make_river_state()

        key = make_information_set_key(state)

        mapping = {
            key: "stored",
        }

        self.assertEqual(
            mapping[key],
            "stored",
        )

    def test_key_string_contains_main_fields(
        self,
    ) -> None:
        state = make_river_state()

        key = make_information_set_key(state)

        text = str(key)

        self.assertIn(
            "P0",
            text,
        )

        self.assertIn(
            "hole=KhQh",
            text,
        )

        self.assertIn(
            "board=Ks8h7d3c2s",
            text,
        )

        self.assertIn(
            "history=root",
            text,
        )

        self.assertIn(
            "pot=100",
            text,
        )

        self.assertIn(
            "stacks=100,100",
            text,
        )

        self.assertIn(
            "committed=0,0",
            text,
        )

        self.assertIn(
            "call=0",
            text,
        )

    def test_key_string_after_bet(
        self,
    ) -> None:
        state = make_river_state()

        state.apply_action(
            Action(
                ActionType.BET,
                amount=50,
            )
        )

        key = make_information_set_key(state)

        text = str(key)

        self.assertIn(
            "P1",
            text,
        )

        self.assertIn(
            "hole=AsJc",
            text,
        )

        self.assertIn(
            "history=bet(50)",
            text,
        )

        self.assertIn(
            "pot=150",
            text,
        )

        self.assertIn(
            "call=50",
            text,
        )


class TestInformationSetCreation(unittest.TestCase):
    def test_create_from_game_state(
        self,
    ) -> None:
        state = make_river_state()

        information_set = make_information_set(state)

        self.assertEqual(
            information_set.key.player_index,
            0,
        )

        self.assertEqual(
            information_set.actions,
            (
                Action(ActionType.CHECK),
                Action(
                    ActionType.BET,
                    amount=50,
                ),
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ),
            ),
        )

    def test_initial_regrets_are_zero(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        self.assertEqual(
            information_set.regrets,
            {
                Action(ActionType.CHECK): 0.0,
                Action(
                    ActionType.BET,
                    amount=50,
                ): 0.0,
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ): 0.0,
            },
        )

    def test_initial_strategy_sum_is_zero(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        for value in information_set.strategy_sum.values():
            self.assertEqual(
                value,
                0.0,
            )

        self.assertEqual(
            information_set.visits,
            0,
        )

    def test_terminal_state_rejected(
        self,
    ) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))

        state.apply_action(Action(ActionType.CHECK))

        self.assertTrue(state.terminal)

        with self.assertRaises(ValueError):
            make_information_set(state)

    def test_empty_action_list_rejected(
        self,
    ) -> None:
        key = InformationSetKey(
            player_index=0,
            hole_cards=tuple(),
            board=tuple(),
            action_history=tuple(),
            pot=0,
            stacks=(100, 100),
            committed=(0, 0),
            to_call=0,
        )

        with self.assertRaises(ValueError):
            InformationSet.create(
                key=key,
                actions=[],
            )

    def test_duplicate_actions_rejected(
        self,
    ) -> None:
        key = InformationSetKey(
            player_index=0,
            hole_cards=tuple(),
            board=tuple(),
            action_history=tuple(),
            pot=0,
            stacks=(100, 100),
            committed=(0, 0),
            to_call=0,
        )

        check = Action(ActionType.CHECK)

        with self.assertRaises(ValueError):
            InformationSet.create(
                key=key,
                actions=[
                    check,
                    check,
                ],
            )


class TestRegretMatching(unittest.TestCase):
    def test_uniform_strategy_when_all_regrets_zero(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        strategy = information_set.current_strategy()

        self.assertAlmostEqual(
            strategy[Action(ActionType.CHECK)],
            1.0 / 3.0,
        )

        self.assertAlmostEqual(
            strategy[
                Action(
                    ActionType.BET,
                    amount=50,
                )
            ],
            1.0 / 3.0,
        )

        self.assertAlmostEqual(
            strategy[
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                )
            ],
            1.0 / 3.0,
        )

        self.assertAlmostEqual(
            sum(strategy.values()),
            1.0,
        )

    def test_positive_regrets_are_normalized(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        check = Action(ActionType.CHECK)

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        all_in = Action(
            ActionType.ALL_IN,
            amount=100,
        )

        information_set.regrets[check] = 1.0

        information_set.regrets[bet] = 2.0

        information_set.regrets[all_in] = 1.0

        strategy = information_set.current_strategy()

        self.assertAlmostEqual(
            strategy[check],
            0.25,
        )

        self.assertAlmostEqual(
            strategy[bet],
            0.50,
        )

        self.assertAlmostEqual(
            strategy[all_in],
            0.25,
        )

    def test_negative_regrets_are_treated_as_zero(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        check = Action(ActionType.CHECK)

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        all_in = Action(
            ActionType.ALL_IN,
            amount=100,
        )

        information_set.regrets[check] = -10.0

        information_set.regrets[bet] = 4.0

        information_set.regrets[all_in] = 0.0

        strategy = information_set.current_strategy()

        self.assertAlmostEqual(
            strategy[check],
            0.0,
        )

        self.assertAlmostEqual(
            strategy[bet],
            1.0,
        )

        self.assertAlmostEqual(
            strategy[all_in],
            0.0,
        )

    def test_all_non_positive_regrets_use_uniform_strategy(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        for action in information_set.actions:
            information_set.regrets[action] = -1.0

        strategy = information_set.current_strategy()

        for probability in strategy.values():
            self.assertAlmostEqual(
                probability,
                1.0 / 3.0,
            )

    def test_add_regret(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        information_set.add_regret(
            bet,
            3.5,
        )

        information_set.add_regret(
            bet,
            -1.0,
        )

        self.assertAlmostEqual(
            information_set.regrets[bet],
            2.5,
        )

    def test_add_regret_rejects_unknown_action(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        unknown_action = Action(
            ActionType.CALL,
            amount=50,
        )

        with self.assertRaises(ValueError):
            information_set.add_regret(
                unknown_action,
                1.0,
            )


class TestAverageStrategy(unittest.TestCase):
    def test_average_strategy_is_uniform_before_updates(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        strategy = information_set.average_strategy()

        for probability in strategy.values():
            self.assertAlmostEqual(
                probability,
                1.0 / 3.0,
            )

    def test_accumulate_strategy(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        check = Action(ActionType.CHECK)

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        all_in = Action(
            ActionType.ALL_IN,
            amount=100,
        )

        strategy = {
            check: 0.2,
            bet: 0.3,
            all_in: 0.5,
        }

        information_set.accumulate_strategy(
            strategy,
            realization_weight=2.0,
        )

        self.assertAlmostEqual(
            information_set.strategy_sum[check],
            0.4,
        )

        self.assertAlmostEqual(
            information_set.strategy_sum[bet],
            0.6,
        )

        self.assertAlmostEqual(
            information_set.strategy_sum[all_in],
            1.0,
        )

        self.assertEqual(
            information_set.visits,
            1,
        )

    def test_average_strategy_after_multiple_updates(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        check = Action(ActionType.CHECK)

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        all_in = Action(
            ActionType.ALL_IN,
            amount=100,
        )

        information_set.accumulate_strategy(
            {
                check: 1.0,
                bet: 0.0,
                all_in: 0.0,
            }
        )

        information_set.accumulate_strategy(
            {
                check: 0.0,
                bet: 0.5,
                all_in: 0.5,
            }
        )

        average = information_set.average_strategy()

        self.assertAlmostEqual(
            average[check],
            0.5,
        )

        self.assertAlmostEqual(
            average[bet],
            0.25,
        )

        self.assertAlmostEqual(
            average[all_in],
            0.25,
        )

    def test_zero_weight_does_not_change_strategy_sum(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        strategy = information_set.current_strategy()

        information_set.accumulate_strategy(
            strategy,
            realization_weight=0.0,
        )

        self.assertTrue(
            all(value == 0.0 for value in information_set.strategy_sum.values())
        )

        self.assertEqual(
            information_set.visits,
            1,
        )

    def test_negative_weight_rejected(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        strategy = information_set.current_strategy()

        with self.assertRaises(ValueError):
            information_set.accumulate_strategy(
                strategy,
                realization_weight=-1.0,
            )

    def test_strategy_missing_action_rejected(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        check = Action(ActionType.CHECK)

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        with self.assertRaises(ValueError):
            information_set.accumulate_strategy(
                {
                    check: 0.5,
                    bet: 0.5,
                }
            )

    def test_strategy_with_unknown_action_rejected(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        check = Action(ActionType.CHECK)

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        all_in = Action(
            ActionType.ALL_IN,
            amount=100,
        )

        fold = Action(ActionType.FOLD)

        with self.assertRaises(ValueError):
            information_set.accumulate_strategy(
                {
                    check: 0.25,
                    bet: 0.25,
                    all_in: 0.25,
                    fold: 0.25,
                }
            )

    def test_negative_probability_rejected(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        check = Action(ActionType.CHECK)

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        all_in = Action(
            ActionType.ALL_IN,
            amount=100,
        )

        with self.assertRaises(ValueError):
            information_set.accumulate_strategy(
                {
                    check: -0.1,
                    bet: 0.6,
                    all_in: 0.5,
                }
            )

    def test_probability_sum_must_equal_one(
        self,
    ) -> None:
        information_set = make_information_set(make_river_state())

        check = Action(ActionType.CHECK)

        bet = Action(
            ActionType.BET,
            amount=50,
        )

        all_in = Action(
            ActionType.ALL_IN,
            amount=100,
        )

        with self.assertRaises(ValueError):
            information_set.accumulate_strategy(
                {
                    check: 0.2,
                    bet: 0.2,
                    all_in: 0.2,
                }
            )


if __name__ == "__main__":
    unittest.main()
