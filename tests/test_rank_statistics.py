from fractions import Fraction
import struct
import unittest
from poker_evaluator.rank_statistics import summarize_chunks


class RankStatisticsTests(unittest.TestCase):
    def test_exact_sum_and_histogram(self):
        result = summarize_chunks([struct.pack('<3H', 1, 2, 2), struct.pack('<2H', 7462, 3)])
        self.assertEqual(result['hand_count'], 5)
        self.assertEqual(result['rank_sum'], 7470)
        self.assertEqual(result['mean_rank'], 1494)
        self.assertEqual(result['rank_counts'], {1:1, 2:2, 3:1, 7462:1})

    def test_fraction_and_chunk_boundaries(self):
        values = struct.pack('<3H', 1, 2, 2)
        one = summarize_chunks([values])
        separate = summarize_chunks([values[:2], values[2:]])
        self.assertEqual(one, separate)
        self.assertEqual(one['mean_rank_fraction'], dict(numerator=5, denominator=3))
        self.assertTrue(one['mean_rank_decimal'].startswith('1.666666666666'))

    def test_invalid_streams(self):
        for chunks in ([], [b'\x01'], [struct.pack('<H', 0)], [struct.pack('<H', 7463)]):
            with self.assertRaises(ValueError):
                summarize_chunks(chunks)

    def test_population_variance_and_exact_fraction(self):
        result = summarize_chunks([struct.pack('<3H', 1, 2, 2)])
        self.assertEqual(result['rank_squared_sum'], 9)
        self.assertEqual(result['variance_rank_fraction'], dict(numerator=2, denominator=9))
        self.assertAlmostEqual(result['variance_rank'], 2/9)
        self.assertAlmostEqual(result['standard_deviation_rank'], (2/9)**.5)

    def test_constant_rank_has_zero_variance(self):
        result = summarize_chunks([struct.pack('<4H', 17, 17, 17, 17)])
        self.assertEqual(result['variance_rank'], 0)
        self.assertEqual(result['standard_deviation_rank'], 0)
