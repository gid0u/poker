import unittest

from poker_evaluator.chance import (
    ChanceDistribution,
    ChanceOutcome,
)
from tests.test_game_tree import (
    make_river_state,
)


class TestChanceOutcome(unittest.TestCase):
    def test_valid_outcome(
        self,
    ) -> None:
        outcome = ChanceOutcome(
            state=make_river_state(),
            probability=0.5,
            label="test",
        )

        self.assertEqual(
            outcome.probability,
            0.5,
        )

        self.assertEqual(
            outcome.label,
            "test",
        )

    def test_negative_probability_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            ChanceOutcome(
                state=make_river_state(),
                probability=-0.1,
            )

    def test_probability_over_one_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            ChanceOutcome(
                state=make_river_state(),
                probability=1.1,
            )


class TestChanceDistribution(unittest.TestCase):
    def test_single_outcome_distribution(
        self,
    ) -> None:
        distribution = ChanceDistribution.create(
            [
                ChanceOutcome(
                    state=make_river_state(),
                    probability=1.0,
                )
            ]
        )

        self.assertEqual(
            len(distribution.outcomes),
            1,
        )

    def test_uniform_distribution(
        self,
    ) -> None:
        distribution = ChanceDistribution.uniform(
            [
                make_river_state(),
                make_river_state(),
            ]
        )

        self.assertEqual(
            len(distribution.outcomes),
            2,
        )

        self.assertAlmostEqual(
            distribution.outcomes[0].probability,
            0.5,
        )

        self.assertAlmostEqual(
            distribution.outcomes[1].probability,
            0.5,
        )

    def test_empty_distribution_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            ChanceDistribution.create([])

    def test_probabilities_must_sum_to_one(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            ChanceDistribution.create(
                [
                    ChanceOutcome(
                        state=make_river_state(),
                        probability=0.4,
                    ),
                    ChanceOutcome(
                        state=make_river_state(),
                        probability=0.4,
                    ),
                ]
            )

    def test_uniform_requires_state(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            ChanceDistribution.uniform([])

    def test_expected_initial_pot(
        self,
    ) -> None:
        state_a = make_river_state()
        state_b = make_river_state()

        state_a.pot = 100
        state_b.pot = 200

        distribution = ChanceDistribution.create(
            [
                ChanceOutcome(
                    state=state_a,
                    probability=0.25,
                ),
                ChanceOutcome(
                    state=state_b,
                    probability=0.75,
                ),
            ]
        )

        self.assertAlmostEqual(
            distribution.expected_initial_pot(),
            175.0,
        )


if __name__ == "__main__":
    unittest.main()
