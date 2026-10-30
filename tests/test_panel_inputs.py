import unittest
from poker_evaluator.card_panel import range_cells, edit_opponent_ranges


class PanelInputTests(unittest.TestCase):
    def test_unsuffixed_range_selects_both_cells(self):
        self.assertEqual(range_cells('AK'), {'AKs', 'AKo'})
        self.assertEqual(range_cells('ka'), {'AKs', 'AKo'})

    def test_plus_ranges_are_visible(self):
        self.assertEqual(range_cells('QQ+, AJs+'), {'QQ','KK','AA','AJs','AQs','AKs'})

    def test_case_whitespace_random_and_empty(self):
        self.assertEqual(range_cells('  RANDOM '), {'random'})
        self.assertEqual(range_cells(''), set())
        self.assertEqual(range_cells(' aa, AKS '), {'AA','AKs'})

    def test_invalid_range_is_not_silently_retained(self):
        with self.assertRaises(ValueError):
            range_cells('not-a-hand')

    def test_append_edit_delete_preserve_other_opponents(self):
        original = ['AA','KK']
        self.assertEqual(edit_opponent_ranges(original,2,'QQ'), ['AA','KK','QQ'])
        self.assertEqual(edit_opponent_ranges(original,0,'AKs'), ['AKs','KK'])
        self.assertEqual(edit_opponent_ranges(original,0,''), ['KK'])
        self.assertEqual(edit_opponent_ranges(original,2,''), original)
        self.assertEqual(original, ['AA','KK'])

    def test_skipped_or_excess_opponents_rejected(self):
        for index in (-1,3,8):
            with self.assertRaises(ValueError):
                edit_opponent_ranges(['AA','KK'], index, 'QQ')
        with self.assertRaises(ValueError):
            edit_opponent_ranges(['AA']*8,8,'QQ')

if __name__ == '__main__': unittest.main()

