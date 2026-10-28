from itertools import combinations
import json
from math import comb
from pathlib import Path
from random import Random
import struct
import tempfile
import unittest

from poker_evaluator.cards import Card, parse_card
from poker_evaluator.rank_table import load_rank_table, rank_seven_cards
from poker_evaluator.seven_card_dictionary import (HAND_COUNT, DATA_FILENAME,
    MANIFEST_FILENAME, SevenCardRankDictionary, hand_index, index_cards)


class IndexTests(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(HAND_COUNT, 133784560)
        self.assertEqual(hand_index(range(7)), 0)
        self.assertEqual(hand_index(range(45, 52)), HAND_COUNT-1)

    def test_all_small_deck_keys_unique_and_contiguous(self):
        indices = {hand_index(c) for c in combinations(range(12), 7)}
        self.assertEqual(indices, set(range(comb(12, 7))))

    def test_index_inverse_and_order_independence(self):
        rng = Random(42)
        for index in [0, HAND_COUNT-1] + rng.sample(range(HAND_COUNT), 1000):
            cards = list(index_cards(index))
            self.assertEqual(hand_index(cards), index)
            rng.shuffle(cards)
            self.assertEqual(hand_index(cards), index)

    def test_invalid_keys(self):
        for cards in ([0]*7, range(6), range(8), [0, 1, 2, 3, 4, 5, 52], [True, 1, 2, 3, 4, 5, 6]):
            with self.assertRaises(ValueError):
                hand_index(cards)
        for index in (-1, HAND_COUNT, 0.5, True):
            with self.assertRaises(ValueError):
                index_cards(index)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.manifest = dict(format="poker-seven-card-colex-u16le-v1", complete=True,
            hand_count=HAND_COUNT, card_encoding="4*(rank-2)+suit; suits=s,c,h,d",
            rank_order="1=strongest;7462=weakest", rank_values=sorted(load_rank_table(), reverse=True))
        (self.path / MANIFEST_FILENAME).write_text(json.dumps(self.manifest))
        with (self.path / DATA_FILENAME).open("wb") as f:
            f.truncate(HAND_COUNT*2)

    def test_reader_lookup_and_value(self):
        hand = "As Ks Qs Js Ts 2c 3d"
        with (self.path / DATA_FILENAME).open("r+b") as f:
            f.seek(2*hand_index(hand))
            f.write(struct.pack("<H", 1))
        with SevenCardRankDictionary(self.path) as table:
            self.assertEqual(len(table), HAND_COUNT)
            self.assertEqual(table[hand], 1)
            self.assertEqual(table.value(hand), (8, 14))
            self.assertEqual(table.category(hand), "straight_flush")
            self.assertEqual(next(iter(table)), tuple(range(7)))
            with self.assertRaises(ValueError):
                table.rank_at(0)

    def test_truncated_and_incomplete_rejected(self):
        (self.path / DATA_FILENAME).write_bytes(b"\0\0")
        with self.assertRaises(ValueError):
            SevenCardRankDictionary(self.path)
        self.manifest["complete"] = False
        (self.path / MANIFEST_FILENAME).write_text(json.dumps(self.manifest))
        with self.assertRaises(ValueError):
            SevenCardRankDictionary(self.path)


class VectorBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from poker_evaluator.seven_card_builder import prepare_tables
        except ImportError:
            raise unittest.SkipTest("Dictionary generation requires optional NumPy")
        cls.tables = prepare_tables()

    def test_pattern_count(self):
        self.assertEqual(len(self.tables[0]), 49205)
        self.assertEqual(len(set(map(int, self.tables[0]))), 49205)

    def test_batch_unranking(self):
        from poker_evaluator.seven_card_builder import unrank_batch
        for begin in (0, 10000, HAND_COUNT-100):
            for offset, ids in enumerate(unrank_batch(begin, begin+100)):
                self.assertEqual(hand_index(map(int, ids)), begin+offset)

    def test_vector_evaluator_against_independent_oracle(self):
        import numpy as np
        from poker_evaluator.seven_card_builder import evaluate_batch
        rng = Random(20261028)
        hands = [sorted(rng.sample(range(52), 7)) for _ in range(2000)]
        # Wheel SF, two triplets, three pairs, 7-card flush and royal with a pair.
        special = ["As 2s 3s 4s 5s Kh Kd", "As Ac Ah Ks Kc Kh 2s",
                   "As Ac Ks Kc Qs Qc 2s", "As Js 9s 7s 5s 3s 2s",
                   "As Ks Qs Js Ts Ac Kc", "As Ac Ah Ad Ks Kc Kh"]
        for hand in special:
            cards = [parse_card(c) for c in hand.split()]
            hands.append(sorted(4*(c.rank-2)+c.suit for c in cards))
        results = evaluate_batch(np.asarray(hands, dtype=np.uint8), self.tables)
        for ids, result in zip(hands, results):
            cards = [Card(i//4+2, i%4) for i in ids]
            self.assertEqual(int(result), rank_seven_cards(cards), ids)


if __name__ == "__main__":
    unittest.main()
