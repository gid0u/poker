import unittest

from poker_evaluator.cards import parse_card
from poker_evaluator.deal_distribution import (
    build_deal_distribution,
    combos_overlap,
    create_state_from_matchup,
    generate_legal_matchups,
)
from poker_evaluator.game_state import Street
from poker_evaluator.range_parser import (
    HandCombo,
    parse_exact_hand,
)


RIVER_BOARD = (
    "Ks",
    "8h",
    "7d",
    "3c",
    "2s",
)

RIVER_BOARD_CARDS = tuple(parse_card(card) for card in RIVER_BOARD)


class TestCombosOverlap(unittest.TestCase):
    def test_overlapping_combos_return_true(
        self,
    ) -> None:
        first = HandCombo(
            parse_card("As"),
            parse_card("Kh"),
        )

        second = HandCombo(
            parse_card("As"),
            parse_card("Qd"),
        )

        self.assertTrue(
            combos_overlap(
                first,
                second,
            )
        )

    def test_non_overlapping_combos_return_false(
        self,
    ) -> None:
        first = HandCombo(
            parse_card("As"),
            parse_card("Kh"),
        )

        second = HandCombo(
            parse_card("Qd"),
            parse_card("Jc"),
        )

        self.assertFalse(
            combos_overlap(
                first,
                second,
            )
        )

    def test_overlap_is_symmetric(
        self,
    ) -> None:
        first = HandCombo(
            parse_card("As"),
            parse_card("Kh"),
        )

        second = HandCombo(
            parse_card("Qd"),
            parse_card("As"),
        )

        self.assertEqual(
            combos_overlap(first, second),
            combos_overlap(second, first),
        )


class TestGenerateLegalMatchups(unittest.TestCase):
    def test_single_fixed_matchup(
        self,
    ) -> None:
        p0_range = (
            HandCombo(
                parse_card("Kh"),
                parse_card("Qh"),
            ),
        )

        p1_range = (
            HandCombo(
                parse_card("As"),
                parse_card("Jc"),
            ),
        )

        matchups = generate_legal_matchups(
            p0_range=p0_range,
            p1_range=p1_range,
            board=RIVER_BOARD,
        )

        self.assertEqual(
            len(matchups),
            1,
        )

        self.assertEqual(
            matchups[0][0],
            p0_range[0],
        )

        self.assertEqual(
            matchups[0][1],
            p1_range[0],
        )

    def test_player_overlap_is_removed(
        self,
    ) -> None:
        p0_range = (
            HandCombo(
                parse_card("As"),
                parse_card("Kh"),
            ),
        )

        p1_range = (
            HandCombo(
                parse_card("As"),
                parse_card("Qd"),
            ),
        )

        matchups = generate_legal_matchups(
            p0_range=p0_range,
            p1_range=p1_range,
            board=(),
        )

        self.assertEqual(
            matchups,
            tuple(),
        )

    def test_board_blocker_is_removed_from_pair_range(
        self,
    ) -> None:
        matchups = generate_legal_matchups(
            p0_range="AA",
            p1_range="QQ",
            board=("As",),
        )

        # Asがブロックされるため、
        # P0のAAは残り3枚から2枚を選ぶ3コンボ。
        # P1のQQは6コンボ。
        self.assertEqual(
            len(matchups),
            18,
        )

        blocked_card = parse_card("As")

        for p0_combo, p1_combo in matchups:
            self.assertFalse(p0_combo.contains(blocked_card))

            self.assertFalse(p1_combo.contains(blocked_card))

    def test_identical_pair_ranges_have_six_matchups(
        self,
    ) -> None:
        matchups = generate_legal_matchups(
            p0_range="AA",
            p1_range="AA",
            board=(),
        )

        # P0が4枚のAから2枚を選ぶ6通り。
        # P1には残り2枚が割り当てられる。
        self.assertEqual(
            len(matchups),
            6,
        )

    def test_disjoint_pair_ranges_have_thirty_six_matchups(
        self,
    ) -> None:
        matchups = generate_legal_matchups(
            p0_range="AA",
            p1_range="KK",
            board=(),
        )

        self.assertEqual(
            len(matchups),
            36,
        )

    def test_river_board_blocks_one_king(
        self,
    ) -> None:
        matchups = generate_legal_matchups(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        # AAは6コンボ。
        # KsがボードにあるのでKKは3コンボ。
        self.assertEqual(
            len(matchups),
            18,
        )

    def test_string_and_combo_ranges_match(
        self,
    ) -> None:
        string_matchups = generate_legal_matchups(
            p0_range="AKs",
            p1_range="QQ",
            board=(),
        )

        combo_matchups = generate_legal_matchups(
            p0_range=parse_exact_hand("AKs"),
            p1_range=parse_exact_hand("QQ"),
            board=(),
        )

        self.assertEqual(
            len(string_matchups),
            len(combo_matchups),
        )

        self.assertEqual(
            set(string_matchups),
            set(combo_matchups),
        )

    def test_card_objects_are_supported_on_board(
        self,
    ) -> None:
        matchups_from_strings = generate_legal_matchups(
            p0_range="AA",
            p1_range="QQ",
            board=RIVER_BOARD,
        )

        matchups_from_cards = generate_legal_matchups(
            p0_range="AA",
            p1_range="QQ",
            board=RIVER_BOARD_CARDS,
        )

        self.assertEqual(
            matchups_from_strings,
            matchups_from_cards,
        )

    def test_duplicate_board_cards_are_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            generate_legal_matchups(
                p0_range="AA",
                p1_range="KK",
                board=(
                    "As",
                    "As",
                ),
            )

    def test_empty_p0_combo_range_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            generate_legal_matchups(
                p0_range=tuple(),
                p1_range="KK",
                board=(),
            )

    def test_empty_p1_combo_range_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            generate_legal_matchups(
                p0_range="AA",
                p1_range=tuple(),
                board=(),
            )

    def test_non_hand_combo_range_item_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            generate_legal_matchups(
                p0_range=("AA",),  # type: ignore[arg-type]
                p1_range="KK",
                board=(),
            )

    def test_duplicate_combos_are_deduplicated(
        self,
    ) -> None:
        combo = HandCombo(
            parse_card("As"),
            parse_card("Ah"),
        )

        matchups = generate_legal_matchups(
            p0_range=(
                combo,
                combo,
            ),
            p1_range=(
                HandCombo(
                    parse_card("Kc"),
                    parse_card("Kd"),
                ),
            ),
            board=(),
        )

        self.assertEqual(
            len(matchups),
            1,
        )


class TestCreateStateFromMatchup(unittest.TestCase):
    def setUp(
        self,
    ) -> None:
        self.p0_combo = HandCombo(
            parse_card("Kh"),
            parse_card("Qh"),
        )

        self.p1_combo = HandCombo(
            parse_card("As"),
            parse_card("Jc"),
        )

    def test_create_river_state(
        self,
    ) -> None:
        state = create_state_from_matchup(
            self.p0_combo,
            self.p1_combo,
            board=RIVER_BOARD,
            stacks=(100, 80),
            pot=120,
            acting_player_index=1,
            street=Street.RIVER,
        )

        self.assertEqual(
            state.players[0].player_id,
            0,
        )

        self.assertEqual(
            state.players[1].player_id,
            1,
        )

        self.assertEqual(
            state.players[0].hole_cards,
            self.p0_combo.cards,
        )

        self.assertEqual(
            state.players[1].hole_cards,
            self.p1_combo.cards,
        )

        self.assertEqual(
            state.players[0].stack,
            100,
        )

        self.assertEqual(
            state.players[1].stack,
            80,
        )

        self.assertEqual(
            state.pot,
            120,
        )

        self.assertEqual(
            state.acting_player_index,
            1,
        )

        self.assertEqual(
            state.street,
            Street.RIVER,
        )

        self.assertEqual(
            state.board,
            RIVER_BOARD_CARDS,
        )

    def test_default_values_create_river_state(
        self,
    ) -> None:
        state = create_state_from_matchup(
            self.p0_combo,
            self.p1_combo,
            board=RIVER_BOARD,
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
            state.pot,
            100,
        )

        self.assertEqual(
            state.acting_player_index,
            0,
        )

        self.assertEqual(
            state.street,
            Street.RIVER,
        )

    def test_card_objects_are_supported_on_board(
        self,
    ) -> None:
        state = create_state_from_matchup(
            self.p0_combo,
            self.p1_combo,
            board=RIVER_BOARD_CARDS,
        )

        self.assertEqual(
            state.board,
            RIVER_BOARD_CARDS,
        )

    def test_overlapping_player_cards_are_rejected(
        self,
    ) -> None:
        invalid_p1_combo = HandCombo(
            parse_card("Kh"),
            parse_card("Jc"),
        )

        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                invalid_p1_combo,
                board=RIVER_BOARD,
            )

    def test_p0_board_overlap_is_rejected(
        self,
    ) -> None:
        invalid_p0_combo = HandCombo(
            parse_card("Ks"),
            parse_card("Qh"),
        )

        with self.assertRaises(ValueError):
            create_state_from_matchup(
                invalid_p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
            )

    def test_p1_board_overlap_is_rejected(
        self,
    ) -> None:
        invalid_p1_combo = HandCombo(
            parse_card("As"),
            parse_card("8h"),
        )

        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                invalid_p1_combo,
                board=RIVER_BOARD,
            )

    def test_duplicate_board_cards_are_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=(
                    "Ks",
                    "Ks",
                    "7d",
                    "3c",
                    "2s",
                ),
            )

    def test_negative_first_stack_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
                stacks=(-1, 100),
            )

    def test_negative_second_stack_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
                stacks=(100, -1),
            )

    def test_non_integer_stack_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
                stacks=(
                    100,
                    50.5,
                ),  # type: ignore[arg-type]
            )

    def test_wrong_stack_count_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
                stacks=(100,),
            )

    def test_negative_pot_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
                pot=-1,
            )

    def test_non_integer_pot_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
                pot=100.5,  # type: ignore[arg-type]
            )

    def test_negative_acting_player_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
                acting_player_index=-1,
            )

    def test_acting_player_over_one_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=RIVER_BOARD,
                acting_player_index=2,
            )

    def test_empty_board_with_river_street_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            create_state_from_matchup(
                self.p0_combo,
                self.p1_combo,
                board=(),
                street=Street.RIVER,
            )


class TestBuildDealDistribution(unittest.TestCase):
    def test_single_matchup_distribution(
        self,
    ) -> None:
        p0_range = (
            HandCombo(
                parse_card("Kh"),
                parse_card("Qh"),
            ),
        )

        p1_range = (
            HandCombo(
                parse_card("As"),
                parse_card("Jc"),
            ),
        )

        distribution = build_deal_distribution(
            p0_range=p0_range,
            p1_range=p1_range,
            board=RIVER_BOARD,
        )

        self.assertEqual(
            len(distribution.outcomes),
            1,
        )

        self.assertAlmostEqual(
            distribution.outcomes[0].probability,
            1.0,
        )

    def test_aa_versus_kk_on_river_board_has_eighteen_outcomes(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        # Ksがボードにあるため、
        # AAの6コンボ × KKの3コンボ。
        self.assertEqual(
            len(distribution.outcomes),
            18,
        )

    def test_probabilities_sum_to_one(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        total_probability = sum(
            outcome.probability for outcome in distribution.outcomes
        )

        self.assertAlmostEqual(
            total_probability,
            1.0,
        )

    def test_distribution_is_uniform(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        expected_probability = 1.0 / 18

        for outcome in distribution.outcomes:
            self.assertAlmostEqual(
                outcome.probability,
                expected_probability,
            )

    def test_outcome_states_have_correct_data(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
            stacks=(150, 75),
            pot=200,
            acting_player_index=1,
            street=Street.RIVER,
        )

        for outcome in distribution.outcomes:
            state = outcome.state

            self.assertEqual(
                state.players[0].stack,
                150,
            )

            self.assertEqual(
                state.players[1].stack,
                75,
            )

            self.assertEqual(
                state.pot,
                200,
            )

            self.assertEqual(
                state.acting_player_index,
                1,
            )

            self.assertEqual(
                state.street,
                Street.RIVER,
            )

            self.assertEqual(
                state.board,
                RIVER_BOARD_CARDS,
            )

    def test_outcomes_have_no_card_overlap(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="TT+",
            p1_range="AJs+",
            board=RIVER_BOARD,
        )

        board_cards = set(RIVER_BOARD_CARDS)

        for outcome in distribution.outcomes:
            state = outcome.state

            p0_cards = set(state.players[0].hole_cards)

            p1_cards = set(state.players[1].hole_cards)

            self.assertTrue(p0_cards.isdisjoint(p1_cards))

            self.assertTrue(p0_cards.isdisjoint(board_cards))

            self.assertTrue(p1_cards.isdisjoint(board_cards))

    def test_labels_are_present(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        for outcome in distribution.outcomes:
            self.assertTrue(outcome.label.startswith("P0="))

            self.assertIn(
                "|P1=",
                outcome.label,
            )

    def test_labels_are_unique_for_aa_versus_kk(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
        )

        labels = [outcome.label for outcome in distribution.outcomes]

        self.assertEqual(
            len(labels),
            len(set(labels)),
        )

    def test_expected_initial_pot(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD,
            pot=175,
        )

        self.assertAlmostEqual(
            distribution.expected_initial_pot(),
            175.0,
        )

    def test_no_legal_matchup_is_rejected(
        self,
    ) -> None:
        p0_range = (
            HandCombo(
                parse_card("As"),
                parse_card("Ah"),
            ),
        )

        p1_range = (
            HandCombo(
                parse_card("As"),
                parse_card("Ah"),
            ),
        )

        with self.assertRaises(ValueError):
            build_deal_distribution(
                p0_range=p0_range,
                p1_range=p1_range,
                board=RIVER_BOARD,
            )

    def test_duplicate_board_cards_are_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            build_deal_distribution(
                p0_range="AA",
                p1_range="KK",
                board=(
                    "Ks",
                    "Ks",
                    "7d",
                    "3c",
                    "2s",
                ),
            )

    def test_empty_board_with_default_river_street_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            build_deal_distribution(
                p0_range="AA",
                p1_range="KK",
                board=(),
            )

    def test_distribution_accepts_card_board(
        self,
    ) -> None:
        distribution = build_deal_distribution(
            p0_range="AA",
            p1_range="KK",
            board=RIVER_BOARD_CARDS,
        )

        self.assertEqual(
            len(distribution.outcomes),
            18,
        )

        for outcome in distribution.outcomes:
            self.assertEqual(
                outcome.state.board,
                RIVER_BOARD_CARDS,
            )


if __name__ == "__main__":
    unittest.main()
