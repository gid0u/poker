import unittest

from poker_evaluator.cfr import CFRTrainer
from poker_evaluator.chance import (
    ChanceDistribution,
    ChanceOutcome,
)
from poker_evaluator.deal_distribution import (
    build_deal_distribution,
)
from tests.test_game_tree import make_river_state


RIVER_BOARD = (
    "Ks",
    "8h",
    "7d",
    "3c",
    "2s",
)


class TestCFRDistributionValidation(unittest.TestCase):
    def test_zero_iterations_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        distribution = ChanceDistribution.uniform(
            [
                make_river_state(),
            ]
        )

        with self.assertRaises(ValueError):
            trainer.train_distribution(
                distribution=distribution,
                iterations=0,
            )

    def test_negative_iterations_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        distribution = ChanceDistribution.uniform(
            [
                make_river_state(),
            ]
        )

        with self.assertRaises(ValueError):
            trainer.train_distribution(
                distribution=distribution,
                iterations=-1,
            )


class TestCFRSingleStateCompatibility(unittest.TestCase):
    def test_train_and_single_state_distribution_match(
        self,
    ) -> None:
        state = make_river_state()

        direct_trainer = CFRTrainer()

        direct_value = direct_trainer.train(
            initial_state=state,
            iterations=100,
        )

        distribution_trainer = CFRTrainer()

        distribution = ChanceDistribution.uniform(
            [
                state,
            ]
        )

        distribution_value = distribution_trainer.train_distribution(
            distribution=distribution,
            iterations=100,
        )

        self.assertAlmostEqual(
            direct_value,
            distribution_value,
        )

    def test_train_updates_iteration_count(
        self,
    ) -> None:
        trainer = CFRTrainer()

        trainer.train(
            initial_state=make_river_state(),
            iterations=25,
        )

        self.assertEqual(
            trainer.iterations_completed,
            25,
        )

    def test_train_updates_overall_utility(
        self,
    ) -> None:
        trainer = CFRTrainer()

        returned_value = trainer.train(
            initial_state=make_river_state(),
            iterations=25,
        )

        self.assertAlmostEqual(
            trainer.overall_average_utility(),
            returned_value,
        )


class TestCFRChanceDistribution(unittest.TestCase):
    def test_distribution_training_completes(
        self,
    ) -> None:
        trainer = CFRTrainer()

        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        value = trainer.train_distribution(
            distribution=distribution,
            iterations=10,
        )

        self.assertIsInstance(
            value,
            float,
        )

        self.assertEqual(
            trainer.iterations_completed,
            10,
        )

        self.assertGreater(
            len(trainer.information_sets),
            0,
        )

    def test_distribution_has_expected_outcome_count(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        # Ksがボード上にあるため、
        # AAは6コンボ、KKは3コンボ。
        self.assertEqual(
            len(distribution.outcomes),
            18,
        )

    def test_distribution_training_does_not_mutate_states(
        self,
    ) -> None:
        trainer = CFRTrainer()

        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        original_histories = [
            list(outcome.state.action_history) for outcome in distribution.outcomes
        ]

        original_terminal_values = [
            outcome.state.terminal for outcome in distribution.outcomes
        ]

        trainer.train_distribution(
            distribution=distribution,
            iterations=10,
        )

        for index, outcome in enumerate(distribution.outcomes):
            self.assertEqual(
                outcome.state.action_history,
                original_histories[index],
            )

            self.assertEqual(
                outcome.state.terminal,
                original_terminal_values[index],
            )

    def test_probabilities_remain_unchanged(
        self,
    ) -> None:
        trainer = CFRTrainer()

        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        original_probabilities = [
            outcome.probability for outcome in distribution.outcomes
        ]

        trainer.train_distribution(
            distribution=distribution,
            iterations=10,
        )

        resulting_probabilities = [
            outcome.probability for outcome in distribution.outcomes
        ]

        self.assertEqual(
            resulting_probabilities,
            original_probabilities,
        )

    def test_information_sets_accumulate_across_iterations(
        self,
    ) -> None:
        trainer = CFRTrainer()

        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        trainer.train_distribution(
            distribution=distribution,
            iterations=1,
        )

        information_set_count = len(trainer.information_sets)

        self.assertGreater(
            information_set_count,
            0,
        )

        trainer.train_distribution(
            distribution=distribution,
            iterations=1,
        )

        self.assertEqual(
            trainer.iterations_completed,
            2,
        )

        self.assertGreaterEqual(
            len(trainer.information_sets),
            information_set_count,
        )

    def test_two_training_calls_track_overall_average(
        self,
    ) -> None:
        trainer = CFRTrainer()

        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        first_value = trainer.train_distribution(
            distribution=distribution,
            iterations=5,
        )

        second_value = trainer.train_distribution(
            distribution=distribution,
            iterations=5,
        )

        expected_overall = (first_value + second_value) / 2.0

        self.assertEqual(
            trainer.iterations_completed,
            10,
        )

        self.assertAlmostEqual(
            trainer.overall_average_utility(),
            expected_overall,
        )

    def test_reset_clears_distribution_training(
        self,
    ) -> None:
        trainer = CFRTrainer()

        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        trainer.train_distribution(
            distribution=distribution,
            iterations=5,
        )

        self.assertGreater(
            len(trainer.information_sets),
            0,
        )

        self.assertEqual(
            trainer.iterations_completed,
            5,
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

        self.assertEqual(
            trainer.overall_average_utility(),
            0.0,
        )


class TestCFRWeightedDistribution(unittest.TestCase):
    def test_weighted_terminal_distribution_value(
        self,
    ) -> None:
        state_a = make_river_state()
        state_b = make_river_state()

        state_a.terminal = True
        state_a.showdown = False
        state_a.winner_index = 0

        state_b.terminal = True
        state_b.showdown = False
        state_b.winner_index = 1

        distribution = ChanceDistribution.create(
            [
                ChanceOutcome(
                    state=state_a,
                    probability=0.75,
                    label="P0 wins",
                ),
                ChanceOutcome(
                    state=state_b,
                    probability=0.25,
                    label="P1 wins",
                ),
            ]
        )

        trainer = CFRTrainer()

        value = trainer.train_distribution(
            distribution=distribution,
            iterations=1,
        )

        expected_value = 0.75 * self._terminal_value(
            state_a
        ) + 0.25 * self._terminal_value(state_b)

        self.assertAlmostEqual(
            value,
            expected_value,
        )

    @staticmethod
    def _terminal_value(
        state,
    ) -> float:
        from poker_evaluator.utility import (
            terminal_utility,
        )

        return terminal_utility(
            state,
            player_index=0,
        )

    def test_zero_probability_outcome_is_skipped(
        self,
    ) -> None:
        active_state = make_river_state()

        skipped_state = make_river_state()
        skipped_state.acting_player_index = 99

        distribution = ChanceDistribution.create(
            [
                ChanceOutcome(
                    state=active_state,
                    probability=1.0,
                    label="active",
                ),
                ChanceOutcome(
                    state=skipped_state,
                    probability=0.0,
                    label="skipped",
                ),
            ]
        )

        trainer = CFRTrainer()

        value = trainer.train_distribution(
            distribution=distribution,
            iterations=1,
        )

        self.assertIsInstance(
            value,
            float,
        )


if __name__ == "__main__":
    unittest.main()
