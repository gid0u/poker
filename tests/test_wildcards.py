from itertools import combinations
from math import comb
import unittest

from poker_evaluator.cards import parse_card
from poker_evaluator.rank_table import rank_seven_cards
from poker_evaluator.wildcards import WildcardPattern, evaluate_wildcards, ExpansionLimitError


class WildcardTests(unittest.TestCase):
    def test_canonical_numbering_and_conditions(self):
        parsed = WildcardPattern.parse("As X9s Qo X2 Xh 2c 3d")
        self.assertEqual(parsed.normalized, "AS X1S QO X2 X3H 2C 3D")

    def test_fixed_hand(self):
        result = evaluate_wildcards("As Ks Qs Js Ts 2c 3d")
        self.assertEqual(result.legal_hands, 1)
        self.assertEqual(result.mean_rank, 1)
        self.assertEqual(result.category_probabilities["straight_flush"], 1)

    def test_one_unknown_uniform_mean(self):
        base = "As Ks Qs Js 2c 3d"
        known = tuple(parse_card(c) for c in base.split())
        ranks = [rank_seven_cards([*known, parse_card(r+s)]) for r in "23456789TJQKA"
                 for s in "schd" if parse_card(r+s) not in known]
        result = evaluate_wildcards(base+" X1")
        self.assertEqual(result.legal_hands, 46)
        self.assertAlmostEqual(result.mean_rank, sum(ranks)/46)
        self.assertAlmostEqual(sum(result.category_probabilities.values()), 1)
        self.assertAlmostEqual(result.expectation(lambda r: 7463-r), result.mean_strength)

    def test_two_unknown_cards_are_sets_not_permutations(self):
        result = list(WildcardPattern.parse("As Ks Qs Js Ts X1 X2").outcomes())
        self.assertEqual(len(result), comb(47, 2))
        self.assertEqual(len({cards for cards, w in result}), comb(47, 2))
        self.assertTrue(all(len(set(cards)) == 7 for cards, w in result))

    def test_suit_limited_unknown(self):
        result = evaluate_wildcards("As Ks Qs Js 2c 3d X2s")
        self.assertEqual(result.legal_hands, 9)

    def test_same_variable_suit_and_reserved_suits(self):
        outcomes = list(WildcardPattern.parse("As Ks Qo Jo 9s 8s 7s").outcomes())
        self.assertEqual(len(outcomes), 3)
        for cards, _ in outcomes:
            q = next(c for c in cards if c.rank == 12)
            j = next(c for c in cards if c.rank == 11)
            self.assertEqual(q.suit, j.suit)
            self.assertNotEqual(q.suit, 0)

    def test_distinct_variable_suits(self):
        outcomes = list(WildcardPattern.parse("As Ko Qp Js 9s 8s 7s").outcomes())
        self.assertEqual(len(outcomes), 6)
        for cards, _ in outcomes:
            k = next(c for c in cards if c.rank == 13)
            q = next(c for c in cards if c.rank == 12)
            self.assertNotEqual(k.suit, q.suit)

    def test_unknown_rank_sharing_variable_suit(self):
        rows = list(WildcardPattern.parse("As Ks Qs Js Ts 2o X1o").outcomes())
        self.assertEqual(len(rows), 36)
        for cards, _ in rows:
            other = [c for c in cards if c.suit != 0]
            self.assertEqual(len(other), 2)
            self.assertEqual(other[0].suit, other[1].suit)
            self.assertEqual(len(set(cards)), 7)

    def test_suit_assignment_dedup_and_overlapping_constraints(self):
        # QO/QP exchanged gives same physical pair: 3 choose 2, not 3*2.
        rows = list(WildcardPattern.parse("As QO QP Js 9s 8s 7s").outcomes())
        self.assertEqual(len(rows), 3)
        # Identical sets reachable with different constrained/unconstrained labels.
        rows = list(WildcardPattern.parse("As Ks Qs Js Ts X1 X2s").outcomes())
        self.assertEqual(len(rows), comb(47, 2)-comb(39, 2))

    def test_explicit_suits_apply_independent_of_token_order(self):
        first = evaluate_wildcards("Qo Jo As Ks 9s 8s 7s")
        second = evaluate_wildcards("As Ks 9s 8s 7s Qo Jo")
        self.assertEqual(first.rank_probabilities, second.rank_probabilities)

    def test_weighted_mean_and_zero_mass(self):
        pattern = "As Ks Qs Js 2c 3d X1s"
        uniform = list(WildcardPattern.parse(pattern).outcomes())
        weights = {"Ts": 5}
        result = evaluate_wildcards(pattern, card_weights=weights)
        expected = sum(rank_seven_cards(cards)*(5 if parse_card("Ts") in cards else 1)
                       for cards, _ in uniform) / 13
        self.assertEqual(result.total_weight, 13)
        self.assertAlmostEqual(result.mean_rank, expected)
        zero = {r+"s": 0 for r in "23456789T"}
        with self.assertRaises(ValueError):
            evaluate_wildcards(pattern, card_weights=zero)

    def test_dead_cards(self):
        result = evaluate_wildcards("As Ks Qs Js 2c 3d X1", dead_cards=["Ts"])
        self.assertEqual(result.legal_hands, 45)
        with self.assertRaises(ValueError):
            evaluate_wildcards("As Ks Qs Js Ts 2c 3d", dead_cards=["As"])

    def test_invalid_patterns_and_impossible_suits(self):
        for pattern in ("As As Qs Js Ts X1 X2", "As Ks Qs Js Ts X1 X1",
                        "As Ks Qs Js Ts X0 X2", "As Ks Qs Js Ts Q X1",
                        "As Kc Qh Jd 9s 8s Qo", "As Ks Qs Js Ts X1"):
            with self.assertRaises(ValueError):
                evaluate_wildcards(pattern)

    def test_no_partial_results_when_budget_exhausted(self):
        with self.assertRaises(ExpansionLimitError):
            evaluate_wildcards("As Ks Qs Js Ts X1 X2", max_candidates=10)

    def test_joint_weight_and_invalid_weights(self):
        result = evaluate_wildcards("As Ks Qs Js 2c 3d X1s",
                                    hand_weight=lambda h: int(parse_card("Ts") in h))
        self.assertEqual(result.legal_hands, 1)
        self.assertEqual(result.mean_rank, 1)
        for weight in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                evaluate_wildcards("As Ks Qs Js 2c 3d X1s", card_weights={"Ts": weight})


if __name__ == "__main__":
    unittest.main()
