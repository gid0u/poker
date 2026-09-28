import unittest

from poker_evaluator.cards import parse_card
from poker_evaluator.range_parser import (
    HandCombo,
    expand_range_token,
    generate_any_suit_combos,
    generate_offsuit_combos,
    generate_pair_combos,
    generate_suited_combos,
    parse_exact_hand,
    parse_range,
    remove_blocked_combos,
)


class TestHandCombo(unittest.TestCase):
    def test_valid_combo(
        self,
    ) -> None:
        combo = HandCombo(
            parse_card("As"),
            parse_card("Kh"),
        )

        self.assertEqual(
            combo.cards,
            (
                parse_card("As"),
                parse_card("Kh"),
            ),
        )

    def test_duplicate_card_rejected(
        self,
    ) -> None:
        card = parse_card("As")

        with self.assertRaises(ValueError):
            HandCombo(
                card,
                card,
            )

    def test_contains(
        self,
    ) -> None:
        combo = HandCombo(
            parse_card("As"),
            parse_card("Kh"),
        )

        self.assertTrue(combo.contains(parse_card("As")))

        self.assertFalse(combo.contains(parse_card("Qd")))

    def test_overlaps(
        self,
    ) -> None:
        combo = HandCombo(
            parse_card("As"),
            parse_card("Kh"),
        )

        self.assertTrue(
            combo.overlaps(
                [
                    parse_card("As"),
                    parse_card("Qd"),
                ]
            )
        )

        self.assertFalse(
            combo.overlaps(
                [
                    parse_card("Qd"),
                    parse_card("Jc"),
                ]
            )
        )


class TestComboGeneration(unittest.TestCase):
    def test_pair_has_six_combos(
        self,
    ) -> None:
        combos = generate_pair_combos("A")

        self.assertEqual(
            len(combos),
            6,
        )

    def test_suited_hand_has_four_combos(
        self,
    ) -> None:
        combos = generate_suited_combos(
            "A",
            "K",
        )

        self.assertEqual(
            len(combos),
            4,
        )

        for combo in combos:
            self.assertEqual(
                combo.first.suit,
                combo.second.suit,
            )

    def test_offsuit_hand_has_twelve_combos(
        self,
    ) -> None:
        combos = generate_offsuit_combos(
            "A",
            "K",
        )

        self.assertEqual(
            len(combos),
            12,
        )

        for combo in combos:
            self.assertNotEqual(
                combo.first.suit,
                combo.second.suit,
            )

    def test_unspecified_hand_has_sixteen_combos(
        self,
    ) -> None:
        combos = generate_any_suit_combos(
            "A",
            "K",
        )

        self.assertEqual(
            len(combos),
            16,
        )

    def test_suited_pair_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            generate_suited_combos(
                "A",
                "A",
            )

    def test_offsuit_pair_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            generate_offsuit_combos(
                "A",
                "A",
            )


class TestRangeTokenExpansion(unittest.TestCase):
    def test_exact_pair(
        self,
    ) -> None:
        self.assertEqual(
            expand_range_token("AA"),
            ("AA",),
        )

    def test_pair_plus(
        self,
    ) -> None:
        self.assertEqual(
            expand_range_token("TT+"),
            (
                "TT",
                "JJ",
                "QQ",
                "KK",
                "AA",
            ),
        )

    def test_exact_suited_hand(
        self,
    ) -> None:
        self.assertEqual(
            expand_range_token("AKs"),
            ("AKs",),
        )

    def test_exact_offsuit_hand(
        self,
    ) -> None:
        self.assertEqual(
            expand_range_token("AKo"),
            ("AKo",),
        )

    def test_suited_plus(
        self,
    ) -> None:
        self.assertEqual(
            expand_range_token("AJs+"),
            (
                "AJs",
                "AQs",
                "AKs",
            ),
        )

    def test_offsuit_plus(
        self,
    ) -> None:
        self.assertEqual(
            expand_range_token("KTo+"),
            (
                "KTo",
                "KJo",
                "KQo",
            ),
        )

    def test_pair_with_suited_suffix_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            expand_range_token("AAs")

    def test_empty_token_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            expand_range_token("")


class TestParseExactHand(unittest.TestCase):
    def test_parse_pair(
        self,
    ) -> None:
        combos = parse_exact_hand("AA")

        self.assertEqual(
            len(combos),
            6,
        )

    def test_parse_suited(
        self,
    ) -> None:
        combos = parse_exact_hand("AKs")

        self.assertEqual(
            len(combos),
            4,
        )

    def test_parse_offsuit(
        self,
    ) -> None:
        combos = parse_exact_hand("AKo")

        self.assertEqual(
            len(combos),
            12,
        )

    def test_parse_unspecified(
        self,
    ) -> None:
        combos = parse_exact_hand("AK")

        self.assertEqual(
            len(combos),
            16,
        )

    def test_reversed_rank_order_is_normalized(
        self,
    ) -> None:
        first = parse_exact_hand("KAo")
        second = parse_exact_hand("AKo")

        self.assertEqual(
            {combo.normalized() for combo in first},
            {combo.normalized() for combo in second},
        )


class TestParseRange(unittest.TestCase):
    def test_single_pair(
        self,
    ) -> None:
        combos = parse_range("AA")

        self.assertEqual(
            len(combos),
            6,
        )

    def test_single_suited_hand(
        self,
    ) -> None:
        combos = parse_range("AKs")

        self.assertEqual(
            len(combos),
            4,
        )

    def test_single_offsuit_hand(
        self,
    ) -> None:
        combos = parse_range("AKo")

        self.assertEqual(
            len(combos),
            12,
        )

    def test_multiple_hands(
        self,
    ) -> None:
        combos = parse_range("AA,KK,AKs")

        self.assertEqual(
            len(combos),
            16,
        )

    def test_pair_plus(
        self,
    ) -> None:
        combos = parse_range("TT+")

        self.assertEqual(
            len(combos),
            30,
        )

    def test_suited_plus(
        self,
    ) -> None:
        combos = parse_range("AJs+")

        self.assertEqual(
            len(combos),
            12,
        )

    def test_offsuit_plus(
        self,
    ) -> None:
        combos = parse_range("KTo+")

        self.assertEqual(
            len(combos),
            36,
        )

    def test_duplicate_ranges_are_deduplicated(
        self,
    ) -> None:
        combos = parse_range("AA,AA")

        self.assertEqual(
            len(combos),
            6,
        )

    def test_overlapping_ranges_are_deduplicated(
        self,
    ) -> None:
        combos = parse_range("TT+,AA")

        self.assertEqual(
            len(combos),
            30,
        )

    def test_whitespace_is_ignored(
        self,
    ) -> None:
        combos = parse_range("  AA , KK , AKs  ")

        self.assertEqual(
            len(combos),
            16,
        )

    def test_newlines_are_supported(
        self,
    ) -> None:
        combos = parse_range("AA\nKK\nAKs")

        self.assertEqual(
            len(combos),
            16,
        )

    def test_empty_range_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError):
            parse_range("")

    def test_non_string_range_rejected(
        self,
    ) -> None:
        with self.assertRaises(TypeError):
            parse_range(123)  # type: ignore[arg-type]


class TestBlockedCards(unittest.TestCase):
    def test_remove_one_blocked_pair_card(
        self,
    ) -> None:
        combos = parse_range("AA")

        filtered = remove_blocked_combos(
            combos,
            [
                parse_card("As"),
            ],
        )

        self.assertEqual(
            len(filtered),
            3,
        )

    def test_remove_one_blocked_suited_card(
        self,
    ) -> None:
        combos = parse_range("AKs")

        filtered = remove_blocked_combos(
            combos,
            [
                parse_card("As"),
            ],
        )

        self.assertEqual(
            len(filtered),
            3,
        )

    def test_remove_board_cards(
        self,
    ) -> None:
        combos = parse_range("AA,KK,AKs")

        filtered = remove_blocked_combos(
            combos,
            [
                parse_card("As"),
                parse_card("Kh"),
            ],
        )

        for combo in filtered:
            self.assertFalse(
                combo.overlaps(
                    [
                        parse_card("As"),
                        parse_card("Kh"),
                    ]
                )
            )

    def test_blocking_does_not_modify_original(
        self,
    ) -> None:
        combos = parse_range("AA")

        remove_blocked_combos(
            combos,
            [
                parse_card("As"),
            ],
        )

        self.assertEqual(
            len(combos),
            6,
        )


if __name__ == "__main__":
    unittest.main()
