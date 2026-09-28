import unittest

from poker_evaluator.actions import (
    Action,
    ActionType,
)
from poker_evaluator.cfr import (
    CFRTrainer,
    format_average_strategies,
    format_strategy,
)
from poker_evaluator.information_set import (
    make_information_set_key,
)
from poker_evaluator.utility import (
    terminal_utility,
)
from tests.test_game_tree import (
    make_river_state,
)


class TestCFRTraversal(unittest.TestCase):
    def test_one_iteration_creates_six_information_sets(
        self,
    ) -> None:
        """
        この固定ゲーム木の非終端状態は6個。

        root
        check
        check-bet
        check-all-in
        bet
        all-in
        """

        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=1,
        )

        self.assertEqual(
            len(trainer.information_sets),
            6,
        )

    def test_one_iteration_updates_iteration_count(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=1,
        )

        self.assertEqual(
            trainer.iterations_completed,
            1,
        )

    def test_multiple_iterations_update_iteration_count(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=10,
        )

        self.assertEqual(
            trainer.iterations_completed,
            10,
        )

        trainer.train(
            make_river_state(),
            iterations=5,
        )

        self.assertEqual(
            trainer.iterations_completed,
            15,
        )

    def test_train_returns_float(
        self,
    ) -> None:
        trainer = CFRTrainer()

        value = trainer.train(
            make_river_state(),
            iterations=1,
        )

        self.assertIsInstance(
            value,
            float,
        )

    def test_initial_state_is_not_modified(
        self,
    ) -> None:
        state = make_river_state()

        trainer = CFRTrainer()

        trainer.train(
            state,
            iterations=10,
        )

        self.assertEqual(
            state.pot,
            100,
        )
        self.assertEqual(
            state.players[0].stack,
            100,
        )
        self.assertEqual(
            state.players[1].stack,
            100,
        )
        self.assertEqual(
            state.action_history,
            [],
        )
        self.assertFalse(state.terminal)

    def test_terminal_state_returns_terminal_utility(
        self,
    ) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        trainer = CFRTrainer()

        expected = terminal_utility(
            state,
            player_index=0,
        )

        actual = trainer.cfr(
            state=state,
            reach_probabilities=(1.0, 1.0),
        )

        self.assertEqual(
            actual,
            expected,
        )
        self.assertEqual(
            len(trainer.information_sets),
            0,
        )

    def test_root_information_set_exists(
        self,
    ) -> None:
        state = make_river_state()
        root_key = make_information_set_key(state)

        trainer = CFRTrainer()

        trainer.train(
            state,
            iterations=1,
        )

        self.assertIn(
            root_key,
            trainer.information_sets,
        )

    def test_root_information_set_has_three_actions(
        self,
    ) -> None:
        state = make_river_state()
        root_key = make_information_set_key(state)

        trainer = CFRTrainer()

        trainer.train(
            state,
            iterations=1,
        )

        information_set = trainer.information_sets[root_key]

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

    def test_regrets_are_updated(
        self,
    ) -> None:
        state = make_river_state()
        root_key = make_information_set_key(state)

        trainer = CFRTrainer()

        trainer.train(
            state,
            iterations=1,
        )

        information_set = trainer.information_sets[root_key]

        self.assertTrue(
            any(regret != 0.0 for regret in information_set.regrets.values())
        )

    def test_strategy_sums_are_updated(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=1,
        )

        for information_set in trainer.information_sets.values():
            self.assertGreater(
                sum(information_set.strategy_sum.values()),
                0.0,
            )

    def test_all_average_strategies_sum_to_one(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=100,
        )

        for information_set in trainer.information_sets.values():
            strategy = information_set.average_strategy()

            self.assertAlmostEqual(
                sum(strategy.values()),
                1.0,
            )

            for probability in strategy.values():
                self.assertGreaterEqual(
                    probability,
                    0.0,
                )
                self.assertLessEqual(
                    probability,
                    1.0,
                )

    def test_all_current_strategies_sum_to_one(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=100,
        )

        for information_set in trainer.information_sets.values():
            strategy = information_set.current_strategy()

            self.assertAlmostEqual(
                sum(strategy.values()),
                1.0,
            )


class TestCFRPublicMethods(unittest.TestCase):
    def test_average_strategy_for_root(
        self,
    ) -> None:
        state = make_river_state()

        trainer = CFRTrainer()

        trainer.train(
            state,
            iterations=100,
        )

        strategy = trainer.average_strategy_for_state(state)

        self.assertEqual(
            set(strategy),
            {
                Action(ActionType.CHECK),
                Action(
                    ActionType.BET,
                    amount=50,
                ),
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ),
            },
        )

        self.assertAlmostEqual(
            sum(strategy.values()),
            1.0,
        )

    def test_current_strategy_for_root(
        self,
    ) -> None:
        state = make_river_state()

        trainer = CFRTrainer()

        trainer.train(
            state,
            iterations=10,
        )

        strategy = trainer.current_strategy_for_state(state)

        self.assertAlmostEqual(
            sum(strategy.values()),
            1.0,
        )

    def test_unknown_state_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        with self.assertRaises(ValueError):
            trainer.average_strategy_for_state(make_river_state())

        with self.assertRaises(ValueError):
            trainer.current_strategy_for_state(make_river_state())

    def test_terminal_state_strategy_rejected(
        self,
    ) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        trainer = CFRTrainer()

        with self.assertRaises(ValueError):
            trainer.average_strategy_for_state(state)

        with self.assertRaises(ValueError):
            trainer.current_strategy_for_state(state)

    def test_get_information_set(
        self,
    ) -> None:
        state = make_river_state()
        key = make_information_set_key(state)

        trainer = CFRTrainer()

        self.assertIsNone(trainer.get_information_set(key))

        trainer.train(
            state,
            iterations=1,
        )

        self.assertIsNotNone(trainer.get_information_set(key))

    def test_overall_average_utility_before_training(
        self,
    ) -> None:
        trainer = CFRTrainer()

        self.assertEqual(
            trainer.overall_average_utility(),
            0.0,
        )

    def test_overall_average_utility_after_training(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=10,
        )

        value = trainer.overall_average_utility()

        self.assertIsInstance(
            value,
            float,
        )

    def test_reset(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=10,
        )

        trainer.reset()

        self.assertEqual(
            trainer.information_sets,
            {},
        )
        self.assertEqual(
            trainer.iterations_completed,
            0,
        )
        self.assertEqual(
            trainer.utility_sum,
            0.0,
        )


class TestCFRValidation(unittest.TestCase):
    def test_zero_iterations_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        with self.assertRaises(ValueError):
            trainer.train(
                make_river_state(),
                iterations=0,
            )

    def test_negative_iterations_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        with self.assertRaises(ValueError):
            trainer.train(
                make_river_state(),
                iterations=-1,
            )

    def test_negative_reach_probability_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        with self.assertRaises(ValueError):
            trainer.cfr(
                state=make_river_state(),
                reach_probabilities=(-0.1, 1.0),
            )

    def test_reach_probability_over_one_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        with self.assertRaises(ValueError):
            trainer.cfr(
                state=make_river_state(),
                reach_probabilities=(1.1, 1.0),
            )


class TestCFRFormatting(unittest.TestCase):
    def test_format_strategy(
        self,
    ) -> None:
        strategy = {
            Action(ActionType.CHECK): 0.25,
            Action(
                ActionType.BET,
                amount=50,
            ): 0.75,
        }

        text = format_strategy(
            strategy,
            decimals=2,
        )

        self.assertEqual(
            text,
            "check=0.25, bet(50)=0.75",
        )

    def test_format_strategy_negative_decimals_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            format_strategy(
                {
                    Action(ActionType.CHECK): 1.0,
                },
                decimals=-1,
            )

    def test_format_average_strategies(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            make_river_state(),
            iterations=10,
        )

        text = format_average_strategies(
            trainer,
            decimals=3,
        )

        self.assertIn(
            "P0",
            text,
        )
        self.assertIn(
            "P1",
            text,
        )
        self.assertIn(
            "check=",
            text,
        )
        self.assertIn(
            "bet(50)=",
            text,
        )
        self.assertIn(
            "all_in(100)=",
            text,
        )

    def test_format_empty_trainer(
        self,
    ) -> None:
        trainer = CFRTrainer()

        self.assertEqual(
            format_average_strategies(trainer),
            "",
        )


if __name__ == "__main__":
    unittest.main()
