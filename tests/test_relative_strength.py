from math import isclose
import unittest
from poker_evaluator.cards import parse_card
from poker_evaluator.range_parser import HandCombo
from poker_evaluator.multiway.deal_distribution import WeightedRange
from poker_evaluator.relative_strength import evaluate_relative_strength, evaluate_relative_wildcards
from poker_evaluator.wildcards import ExpansionLimitError

BOARD = 'Ks 8h 7d 3c 2s'
HERO = 'As Ah'


def hand(text):
    return HandCombo(*(parse_card(c) for c in text.split()))


class RelativeStrengthTests(unittest.TestCase):
    def test_same_rank_different_relative_strength(self):
        weak = evaluate_relative_strength(HERO, BOARD, ['QQ'], mode='exact')
        strong = evaluate_relative_strength(HERO, BOARD, ['KK'], mode='exact')
        mixed = evaluate_relative_strength(HERO, BOARD, ['KK,QQ'], mode='exact')
        self.assertEqual(weak.mean_rank, strong.mean_rank)
        self.assertEqual(weak.variance_rank, 0)
        self.assertEqual(strong.variance_rank, 0)
        self.assertEqual(weak.equity, 1)
        self.assertEqual(strong.equity, 0)
        self.assertAlmostEqual(mixed.equity, 2/3)
        self.assertAlmostEqual(mixed.win_probability+mixed.tie_probability+mixed.loss_probability, 1)

    def test_split_pot_is_not_full_win(self):
        result = evaluate_relative_strength('2c 3d', 'As Ks Qs Js Ts',
            [[hand('4c 5d')], [hand('6c 7d')]], mode='exact')
        self.assertEqual(result.win_probability, 0)
        self.assertEqual(result.tie_probability, 1)
        self.assertEqual(result.loss_probability, 0)
        self.assertAlmostEqual(result.equity, 1/3)

    def test_nine_player_limit_and_nine_way_split(self):
        opponents = [[hand(rank+'c '+rank+'d')] for rank in '456789TJ']
        result = evaluate_relative_strength('2c 3d', 'As Ks Qs Js Ts', opponents, mode='exact')
        self.assertEqual(result.conditions['opponent_count'], 8)
        self.assertEqual(result.outcomes, 1)
        self.assertEqual(result.tie_probability, 1)
        self.assertAlmostEqual(result.equity, 1/9)
        with self.assertRaises(ValueError):
            evaluate_relative_strength('2c 3d', 'As Ks Qs Js Ts', opponents + [[hand('Qc Qd')]], mode='exact')

    def test_joint_collisions_not_sequential_renormalization(self):
        ranges = [[hand('Kc Kh'), hand('Qc Qh')], [hand('Kc Kd'), hand('Jc Jh')]]
        exact = evaluate_relative_strength(HERO, BOARD, ranges, mode='exact')
        self.assertEqual(exact.outcomes, 3)
        self.assertAlmostEqual(exact.equity, 1/3)
        # Cheap hand evaluator for sampling tests still distinguishes trip kings.
        score = lambda cards: 1 if sum(c.rank == 13 for c in cards) == 3 else (2 if sum(c.rank == 14 for c in cards) == 2 else 3)
        sampled = evaluate_relative_strength(HERO, BOARD, ranges, samples=5000, seed=71, ranker=score)
        self.assertLess(abs(sampled.equity-exact.equity), 5*sampled.equity_standard_error)
        repeated = evaluate_relative_strength(HERO, BOARD, ranges, samples=5000, seed=71, ranker=score)
        self.assertEqual(sampled, repeated)

    def test_weighted_range(self):
        ranges = [WeightedRange(((hand('Kc Kh'), 3), (hand('Qc Qh'), 1)))]
        result = evaluate_relative_strength(HERO, BOARD, ranges, mode='exact')
        self.assertAlmostEqual(result.equity, .25)

    def test_turn_runouts_and_dead_cards(self):
        result = evaluate_relative_strength(HERO, 'Ks 8h 7d 3c', [[hand('Kc Kh')]], mode='exact')
        # Hero wins only when one of the two remaining aces hits the river.
        self.assertEqual(result.outcomes, 44)
        self.assertAlmostEqual(result.equity, 2/44)
        dead = evaluate_relative_strength(HERO, 'Ks 8h 7d 3c', [[hand('Kc Kh')]],
                                         dead_cards=['Ac'], mode='exact')
        self.assertEqual(dead.outcomes, 43)
        self.assertAlmostEqual(dead.equity, 1/43)
        self.assertGreater(result.variance_rank, 0)

    def test_wildcards_match_observed_turn(self):
        explicit = evaluate_relative_strength(HERO, 'Ks 8h 7d 3c', [[hand('Kc Kh')]], mode='exact')
        wild = evaluate_relative_wildcards('As Ah Ks 8h 7d 3c X1', [[hand('Kc Kh')]])
        self.assertAlmostEqual(explicit.mean_rank, wild.mean_rank)
        self.assertAlmostEqual(explicit.variance_rank, wild.variance_rank)
        self.assertAlmostEqual(explicit.equity, wild.equity)
        self.assertEqual(explicit.outcomes, wild.outcomes)

    def test_suit_variable_relative_evaluation(self):
        result = evaluate_relative_wildcards('As Ks Qo Jo 9s 8s 7s', [[hand('2c 3d')]])
        self.assertEqual(result.outcomes, 3)
        self.assertEqual(result.equity, 1)

    def test_random_range_full_river_count(self):
        result = evaluate_relative_strength(HERO, BOARD, ['random'], mode='exact', ranker=lambda c: 1)
        self.assertEqual(result.outcomes, 990)
        self.assertEqual(result.equity, .5)

    def test_no_legal_deals_rejected(self):
        ranges = [[hand('Qc Qh')], [hand('Qc Qh')]]
        with self.assertRaises(ValueError):
            evaluate_relative_strength(HERO, BOARD, ranges, mode='exact')
        with self.assertRaises(ValueError):
            evaluate_relative_strength(HERO, BOARD, ranges, samples=2, max_attempts=10)

    def test_invalid_and_limits(self):
        for hero, board in [('As As', BOARD), (HERO, 'As 8h 7d'), (HERO, '8h 7d')]:
            with self.assertRaises(ValueError):
                evaluate_relative_strength(hero, board, ['KK'])
        with self.assertRaises(ValueError):
            evaluate_relative_strength(HERO, BOARD, ['KK'], samples=1)
        with self.assertRaises(ExpansionLimitError):
            evaluate_relative_strength(HERO, [], ['KK'], mode='exact', max_candidates=10)


if __name__ == '__main__':
    unittest.main()
