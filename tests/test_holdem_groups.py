from itertools import permutations
from math import comb, perm
import unittest

from poker_evaluator.wildcards import (HOLDEM_GROUPS, WildcardPattern,
    evaluate_wildcards, evaluate_holdem_wildcards)


class HoldemGroupTests(unittest.TestCase):
    def test_group_enumeration_matches_brute_force_and_removes_factorials(self):
        pattern = WildcardPattern.parse("X1 X2 X3 X4 X5 X6 X7")
        rows = list(pattern.outcomes(dead_cards=range(8, 52), group_sizes=HOLDEM_GROUPS))
        keys = {(tuple(4*(c.rank-2)+c.suit for c in cards[:2]),
                 tuple(4*(c.rank-2)+c.suit for c in cards[2:5]),
                 4*(cards[5].rank-2)+cards[5].suit,
                 4*(cards[6].rank-2)+cards[6].suit) for cards, mass in rows}
        brute = {(tuple(sorted(p[:2])), tuple(sorted(p[2:5])), p[5], p[6])
                 for p in permutations(range(8), 7)}
        self.assertEqual(keys, brute)
        self.assertEqual(len(rows), perm(8, 7)//12)
        self.assertEqual(len(rows), comb(8, 2)*comb(6, 3)*3*2)

    def test_turn_and_river_are_distinct_but_hole_pair_is_unordered(self):
        river = evaluate_holdem_wildcards("As Ks Qs Js Ts X1 X2", ranker=lambda c: 1)
        holes = evaluate_holdem_wildcards("X1 X2 Qs Js Ts As Ks", ranker=lambda c: 1)
        self.assertEqual(river.legal_hands, 47*46)
        self.assertEqual(holes.legal_hands, comb(47, 2))

    def test_final_hand_evaluated_once_for_different_reveal_partitions(self):
        calls = []
        def ranker(cards):
            calls.append(cards)
            return sum(4*(c.rank-2)+c.suit for c in cards)+1
        result = evaluate_holdem_wildcards("X1 X2 X3 X4 X5 X6 X7",
                                         dead_cards=range(8, 52), ranker=ranker)
        self.assertEqual(result.legal_hands, 3360)
        self.assertEqual(len(calls), 8)
        whole = evaluate_wildcards("X1 X2 X3 X4 X5 X6 X7", dead_cards=range(8, 52), ranker=ranker)
        self.assertAlmostEqual(result.mean_rank, whole.mean_rank)

    def test_role_dependent_weights_preserved(self):
        # Only states whose turn is 2s are given positive mass.
        result = evaluate_holdem_wildcards("X1 X2 X3 X4 X5 X6 X7", dead_cards=range(8, 52),
            ranker=lambda cards: 1, hand_weight=lambda cards: int(cards[5].rank == 2 and cards[5].suit == 0))
        self.assertEqual(result.legal_hands, comb(7, 2)*comb(5, 3)*2)

    def test_constraints_within_hole_group_deduplicated(self):
        rows = list(WildcardPattern.parse("X1 X2s As Ks Qs Js Ts").outcomes(group_sizes=HOLDEM_GROUPS))
        self.assertEqual(len(rows), comb(47, 2)-comb(39, 2))

    def test_invalid_group_definitions(self):
        for sizes in ((), (2, 3), (2, 3, 0, 2), (True, 6), (-1, 8)):
            with self.assertRaises(ValueError):
                evaluate_wildcards("As Ks Qs Js Ts 2c 3d", group_sizes=sizes)


if __name__ == "__main__":
    unittest.main()
