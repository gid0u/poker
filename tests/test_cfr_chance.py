import unittest

from poker_evaluator.cards import (
    parse_card,
)
from poker_evaluator.cfr import (
    CFRTrainer,
)
from poker_evaluator.chance import (
    ChanceDistribution,
    ChanceOutcome,
)
from poker_evaluator.information_set import (
    make_information_set_key,
)
from tests.test_game_tree import (
    make_river_state,
)


def make_state_with_p1_cards(
    first_card: str,
    second_card: str,
):
    state = make_river_state()

    state.players[1].hole_cards = (
        parse_card(first_card),
        parse_card(second_card),
    )

    return state


class TestCFRChanceDistribution(unittest.TestCase):
    def test_single_state_train_still_works(
        self,
    ) -> None:
        trainer = CFRTrainer()

        value = trainer.train(
            make_river_state(),
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

    def test_distribution_training_updates_iterations(
        self,
    ) -> None:
        distribution = ChanceDistribution.uniform(
            [
                make_river_state(),
                make_state_with_p1_cards(
                    "Ah",
                    "Td",
                ),
            ]
        )

        trainer = CFRTrainer()

        trainer.train_distribution(
            distribution=distribution,
            iterations=20,
        )

        self.assertEqual(
            trainer.iterations_completed,
            20,
        )

    def test_p0_root_information_set_is_shared(
        self,
    ) -> None:
        state_a = make_state_with_p1_cards(
            "As",
            "Jc",
        )

        state_b = make_state_with_p1_cards(
            "Ah",
            "Td",
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

        distribution = ChanceDistribution.uniform(
            [
                state_a,
                state_b,
            ]
        )

        trainer = CFRTrainer()

        trainer.train_distribution(
            distribution=distribution,
            iterations=1,
        )

        self.assertIn(
            key_a,
            trainer.information_sets,
        )

        root_information_sets = [
            key
            for key in trainer.information_sets
            if (key.player_index == 0 and key.action_history == tuple())
        ]

        self.assertEqual(
            len(root_information_sets),
            1,
        )

    def test_p1_information_sets_depend_on_own_cards(
        self,
    ) -> None:
        state_a = make_state_with_p1_cards(
            "As",
            "Jc",
        )

        state_b = make_state_with_p1_cards(
            "Ah",
            "Td",
        )

        distribution = ChanceDistribution.uniform(
            [
                state_a,
                state_b,
            ]
        )

        trainer = CFRTrainer()

        trainer.train_distribution(
            distribution=distribution,
            iterations=1,
        )

        p1_after_check_keys = [
            key
            for key in trainer.information_sets
            if (key.player_index == 1 and key.action_history == ("check",))
        ]

        self.assertEqual(
            len(p1_after_check_keys),
            2,
        )

        hole_cards = {key.hole_cards for key in p1_after_check_keys}

        self.assertEqual(
            hole_cards,
            {
                ("As", "Jc"),
                ("Ah", "Td"),
            },
        )

    def test_zero_probability_outcome_is_ignored(
        self,
    ) -> None:
        state_positive = make_river_state()

        state_zero = make_state_with_p1_cards(
            "Ah",
            "Td",
        )

        distribution = ChanceDistribution.create(
            [
                ChanceOutcome(
                    state=state_positive,
                    probability=1.0,
                ),
                ChanceOutcome(
                    state=state_zero,
                    probability=0.0,
                ),
            ]
        )

        trainer = CFRTrainer()

        trainer.train_distribution(
            distribution=distribution,
            iterations=1,
        )

        zero_state_p1_key = make_information_set_key(
            state_zero,
            player_index=1,
        )

        self.assertNotIn(
            zero_state_p1_key,
            trainer.information_sets,
        )

    def test_negative_chance_reach_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        with self.assertRaises(ValueError):
            trainer.cfr(
                state=make_river_state(),
                reach_probabilities=(1.0, 1.0),
                chance_reach=-0.1,
            )

    def test_chance_reach_over_one_rejected(
        self,
    ) -> None:
        trainer = CFRTrainer()

        with self.assertRaises(ValueError):
            trainer.cfr(
                state=make_river_state(),
                reach_probabilities=(1.0, 1.0),
                chance_reach=1.1,
            )


if __name__ == "__main__":
    unittest.main()
