import unittest

from poker_evaluator.cards import (
    parse_card,
)
from poker_evaluator.deck import (
    Deck,
    full_deck_cards,
)


class TestFullDeckCards(unittest.TestCase):
    def test_full_deck_has_52_cards(
        self,
    ) -> None:
        cards = full_deck_cards()

        self.assertEqual(
            len(cards),
            52,
        )

    def test_full_deck_has_no_duplicates(
        self,
    ) -> None:
        cards = full_deck_cards()

        self.assertEqual(
            len(set(cards)),
            52,
        )

    def test_all_ranks_exist_four_times(
        self,
    ) -> None:
        cards = full_deck_cards()

        for rank in range(2, 15):
            matching_cards = [card for card in cards if card.rank == rank]

            self.assertEqual(
                len(matching_cards),
                4,
            )

    def test_all_suits_exist_thirteen_times(
        self,
    ) -> None:
        cards = full_deck_cards()

        for suit in range(4):
            matching_cards = [card for card in cards if card.suit == suit]

            self.assertEqual(
                len(matching_cards),
                13,
            )


class TestDeckCreation(unittest.TestCase):
    def test_create_standard_deck(
        self,
    ) -> None:
        deck = Deck.create()

        self.assertEqual(
            len(deck),
            52,
        )

    def test_from_cards(
        self,
    ) -> None:
        cards = [
            parse_card("As"),
            parse_card("Kh"),
        ]

        deck = Deck.from_cards(cards)

        self.assertEqual(
            len(deck),
            2,
        )

        self.assertIn(
            parse_card("As"),
            deck,
        )

        self.assertIn(
            parse_card("Kh"),
            deck,
        )

    def test_from_cards_rejects_duplicates(
        self,
    ) -> None:
        ace_spades = parse_card("As")

        with self.assertRaises(ValueError):
            Deck.from_cards(
                [
                    ace_spades,
                    ace_spades,
                ]
            )

    def test_clone_is_independent(
        self,
    ) -> None:
        deck = Deck.create()
        cloned = deck.clone()

        cloned.remove(parse_card("As"))

        self.assertEqual(
            len(deck),
            52,
        )

        self.assertEqual(
            len(cloned),
            51,
        )

        self.assertIn(
            parse_card("As"),
            deck,
        )

        self.assertNotIn(
            parse_card("As"),
            cloned,
        )


class TestDeckRemoval(unittest.TestCase):
    def test_remove_one_card(
        self,
    ) -> None:
        deck = Deck.create()

        ace_spades = parse_card("As")

        deck.remove(ace_spades)

        self.assertEqual(
            len(deck),
            51,
        )

        self.assertNotIn(
            ace_spades,
            deck,
        )

    def test_remove_missing_card_rejected(
        self,
    ) -> None:
        deck = Deck.create()

        ace_spades = parse_card("As")

        deck.remove(ace_spades)

        with self.assertRaises(ValueError):
            deck.remove(ace_spades)

    def test_remove_many(
        self,
    ) -> None:
        deck = Deck.create()

        removed_cards = [
            parse_card("As"),
            parse_card("Kh"),
            parse_card("Qd"),
        ]

        deck.remove_many(removed_cards)

        self.assertEqual(
            len(deck),
            49,
        )

        for card in removed_cards:
            self.assertNotIn(
                card,
                deck,
            )

    def test_remove_many_rejects_duplicate_input(
        self,
    ) -> None:
        deck = Deck.create()

        ace_spades = parse_card("As")

        with self.assertRaises(ValueError):
            deck.remove_many(
                [
                    ace_spades,
                    ace_spades,
                ]
            )

        self.assertEqual(
            len(deck),
            52,
        )

        self.assertIn(
            ace_spades,
            deck,
        )

    def test_remove_many_rejects_missing_card(
        self,
    ) -> None:
        deck = Deck.create()

        missing_card = parse_card("Kh")

        deck.remove(missing_card)

        with self.assertRaises(ValueError):
            deck.remove_many(
                [
                    parse_card("As"),
                    missing_card,
                ]
            )

    def test_remove_many_is_atomic(
        self,
    ) -> None:
        deck = Deck.create()

        valid_card = parse_card("As")
        missing_card = parse_card("Kh")

        deck.remove(missing_card)

        original_cards = list(deck.cards)

        with self.assertRaises(ValueError):
            deck.remove_many(
                [
                    valid_card,
                    missing_card,
                ]
            )

        self.assertEqual(
            deck.cards,
            original_cards,
        )

        self.assertIn(
            valid_card,
            deck,
        )

        self.assertNotIn(
            missing_card,
            deck,
        )

        self.assertEqual(
            len(deck),
            51,
        )


class TestDeckDraw(unittest.TestCase):
    def test_draw_one_card(
        self,
    ) -> None:
        deck = Deck.create()

        drawn = deck.draw()

        self.assertEqual(
            len(drawn),
            1,
        )

        self.assertEqual(
            len(deck),
            51,
        )

        self.assertNotIn(
            drawn[0],
            deck,
        )

    def test_draw_multiple_cards(
        self,
    ) -> None:
        deck = Deck.create()

        drawn = deck.draw(5)

        self.assertEqual(
            len(drawn),
            5,
        )

        self.assertEqual(
            len(deck),
            47,
        )

        self.assertEqual(
            len(set(drawn)),
            5,
        )

        for card in drawn:
            self.assertNotIn(
                card,
                deck,
            )

    def test_draw_returns_cards_from_deck_front(
        self,
    ) -> None:
        deck = Deck.create()

        expected = tuple(deck.cards[:3])

        drawn = deck.draw(3)

        self.assertEqual(
            drawn,
            expected,
        )

    def test_draw_zero_cards(
        self,
    ) -> None:
        deck = Deck.create()

        drawn = deck.draw(0)

        self.assertEqual(
            drawn,
            tuple(),
        )

        self.assertEqual(
            len(deck),
            52,
        )

    def test_draw_all_cards(
        self,
    ) -> None:
        deck = Deck.create()

        drawn = deck.draw(52)

        self.assertEqual(
            len(drawn),
            52,
        )

        self.assertEqual(
            len(deck),
            0,
        )

        self.assertEqual(
            len(set(drawn)),
            52,
        )

    def test_draw_too_many_cards_rejected(
        self,
    ) -> None:
        deck = Deck.create()

        with self.assertRaises(ValueError):
            deck.draw(53)

        self.assertEqual(
            len(deck),
            52,
        )

    def test_negative_draw_rejected(
        self,
    ) -> None:
        deck = Deck.create()

        with self.assertRaises(ValueError):
            deck.draw(-1)

        self.assertEqual(
            len(deck),
            52,
        )


class TestDeckSample(unittest.TestCase):
    def test_sample_does_not_change_deck(
        self,
    ) -> None:
        deck = Deck.create()

        original_cards = list(deck.cards)

        sampled = deck.sample(
            count=5,
            seed=42,
        )

        self.assertEqual(
            len(sampled),
            5,
        )

        self.assertEqual(
            len(set(sampled)),
            5,
        )

        self.assertEqual(
            deck.cards,
            original_cards,
        )

        self.assertEqual(
            len(deck),
            52,
        )

    def test_sample_is_deterministic_with_seed(
        self,
    ) -> None:
        deck = Deck.create()

        first_sample = deck.sample(
            count=5,
            seed=123,
        )

        second_sample = deck.sample(
            count=5,
            seed=123,
        )

        self.assertEqual(
            first_sample,
            second_sample,
        )

    def test_sample_contains_only_available_cards(
        self,
    ) -> None:
        deck = Deck.create()

        deck.remove_many(
            [
                parse_card("As"),
                parse_card("Kh"),
            ]
        )

        sampled = deck.sample(
            count=10,
            seed=10,
        )

        for card in sampled:
            self.assertIn(
                card,
                deck,
            )

        self.assertNotIn(
            parse_card("As"),
            sampled,
        )

        self.assertNotIn(
            parse_card("Kh"),
            sampled,
        )

    def test_sample_zero_cards(
        self,
    ) -> None:
        deck = Deck.create()

        sampled = deck.sample(
            count=0,
            seed=42,
        )

        self.assertEqual(
            sampled,
            tuple(),
        )

        self.assertEqual(
            len(deck),
            52,
        )

    def test_sample_all_cards(
        self,
    ) -> None:
        deck = Deck.create()

        sampled = deck.sample(
            count=52,
            seed=42,
        )

        self.assertEqual(
            len(sampled),
            52,
        )

        self.assertEqual(
            len(set(sampled)),
            52,
        )

        self.assertEqual(
            set(sampled),
            set(deck.cards),
        )

        self.assertEqual(
            len(deck),
            52,
        )

    def test_sample_too_many_cards_rejected(
        self,
    ) -> None:
        deck = Deck.create()

        with self.assertRaises(ValueError):
            deck.sample(count=53)

    def test_negative_sample_rejected(
        self,
    ) -> None:
        deck = Deck.create()

        with self.assertRaises(ValueError):
            deck.sample(count=-1)


class TestDeckShuffle(unittest.TestCase):
    def test_shuffled_does_not_change_original(
        self,
    ) -> None:
        deck = Deck.create()

        original_order = tuple(deck.cards)

        shuffled = deck.shuffled(seed=42)

        self.assertEqual(
            tuple(deck.cards),
            original_order,
        )

        self.assertNotEqual(
            tuple(shuffled.cards),
            original_order,
        )

    def test_shuffled_contains_same_cards(
        self,
    ) -> None:
        deck = Deck.create()

        shuffled = deck.shuffled(seed=42)

        self.assertEqual(
            set(deck.cards),
            set(shuffled.cards),
        )

        self.assertEqual(
            len(shuffled),
            52,
        )

    def test_shuffled_is_deterministic_with_seed(
        self,
    ) -> None:
        deck = Deck.create()

        first = deck.shuffled(seed=42)

        second = deck.shuffled(seed=42)

        self.assertEqual(
            first.cards,
            second.cards,
        )

    def test_shuffled_returns_independent_deck(
        self,
    ) -> None:
        deck = Deck.create()

        shuffled = deck.shuffled(seed=42)

        shuffled.remove(shuffled.cards[0])

        self.assertEqual(
            len(deck),
            52,
        )

        self.assertEqual(
            len(shuffled),
            51,
        )

    def test_shuffle_changes_current_deck(
        self,
    ) -> None:
        deck = Deck.create()

        original_order = tuple(deck.cards)

        deck.shuffle(seed=42)

        self.assertNotEqual(
            tuple(deck.cards),
            original_order,
        )

        self.assertEqual(
            len(deck),
            52,
        )

    def test_shuffle_preserves_cards(
        self,
    ) -> None:
        deck = Deck.create()

        original_cards = set(deck.cards)

        deck.shuffle(seed=42)

        self.assertEqual(
            set(deck.cards),
            original_cards,
        )

    def test_shuffle_is_deterministic_with_seed(
        self,
    ) -> None:
        first = Deck.create()
        second = Deck.create()

        first.shuffle(seed=123)

        second.shuffle(seed=123)

        self.assertEqual(
            first.cards,
            second.cards,
        )


class TestDeckCombinations(unittest.TestCase):
    def test_two_card_combinations_from_full_deck(
        self,
    ) -> None:
        deck = Deck.create()

        combinations_list = list(deck.combinations(2))

        self.assertEqual(
            len(combinations_list),
            1326,
        )

    def test_one_card_combinations_from_full_deck(
        self,
    ) -> None:
        deck = Deck.create()

        combinations_list = list(deck.combinations(1))

        self.assertEqual(
            len(combinations_list),
            52,
        )

    def test_zero_card_combinations(
        self,
    ) -> None:
        deck = Deck.create()

        combinations_list = list(deck.combinations(0))

        self.assertEqual(
            combinations_list,
            [tuple()],
        )

    def test_hole_card_combinations(
        self,
    ) -> None:
        deck = Deck.create()

        combinations_list = list(deck.hole_card_combinations())

        self.assertEqual(
            len(combinations_list),
            1326,
        )

        for combo in combinations_list:
            self.assertEqual(
                len(combo),
                2,
            )

            self.assertNotEqual(
                combo[0],
                combo[1],
            )

    def test_hole_card_combinations_have_no_duplicates(
        self,
    ) -> None:
        deck = Deck.create()

        combinations_list = list(deck.hole_card_combinations())

        normalized = {frozenset(combo) for combo in combinations_list}

        self.assertEqual(
            len(normalized),
            1326,
        )

    def test_combinations_after_card_removal(
        self,
    ) -> None:
        deck = Deck.create()

        deck.remove_many(
            [
                parse_card("Ks"),
                parse_card("8h"),
                parse_card("7d"),
                parse_card("3c"),
                parse_card("2s"),
                parse_card("Kh"),
                parse_card("Qh"),
            ]
        )

        combinations_list = list(deck.hole_card_combinations())

        self.assertEqual(
            len(deck),
            45,
        )

        self.assertEqual(
            len(combinations_list),
            990,
        )

    def test_combinations_do_not_modify_deck(
        self,
    ) -> None:
        deck = Deck.create()

        original_cards = list(deck.cards)

        list(deck.combinations(2))

        self.assertEqual(
            deck.cards,
            original_cards,
        )

        self.assertEqual(
            len(deck),
            52,
        )

    def test_combination_count_larger_than_deck_returns_empty(
        self,
    ) -> None:
        deck = Deck.from_cards(
            [
                parse_card("As"),
                parse_card("Kh"),
            ]
        )

        combinations_list = list(deck.combinations(3))

        self.assertEqual(
            combinations_list,
            [],
        )

    def test_invalid_negative_combination_count(
        self,
    ) -> None:
        deck = Deck.create()

        with self.assertRaises(ValueError):
            list(deck.combinations(-1))


class TestDeckProtocolMethods(unittest.TestCase):
    def test_len(
        self,
    ) -> None:
        deck = Deck.create()

        self.assertEqual(
            len(deck),
            52,
        )

        deck.remove(parse_card("As"))

        self.assertEqual(
            len(deck),
            51,
        )

    def test_contains(
        self,
    ) -> None:
        deck = Deck.create()

        ace_spades = parse_card("As")

        self.assertIn(
            ace_spades,
            deck,
        )

        deck.remove(ace_spades)

        self.assertNotIn(
            ace_spades,
            deck,
        )

    def test_iter(
        self,
    ) -> None:
        deck = Deck.create()

        iterated_cards = list(deck)

        self.assertEqual(
            iterated_cards,
            deck.cards,
        )

        self.assertEqual(
            len(iterated_cards),
            52,
        )


if __name__ == "__main__":
    unittest.main()
