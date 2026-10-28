from dataclasses import asdict
import json
from math import comb, perm
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary

with SevenCardRankDictionary() as table:
    pattern = "X1 X2 X3 X4 X5 X6 X7"
    unordered = table.evaluate_wildcards(pattern)
    grouped = table.evaluate_wildcards(pattern, group_sizes=(2, 3, 1, 1))
assert grouped.legal_hands == comb(52, 2)*comb(50, 3)*47*46
assert grouped.legal_hands*12 == perm(52, 7)
assert grouped.legal_hands == unordered.legal_hands*420
assert abs(grouped.mean_rank-unordered.mean_rank) < 1e-10
for rank, probability in unordered.rank_probabilities.items():
    assert abs(probability-grouped.rank_probabilities[rank]) < 1e-14
result = dict(fully_ordered=perm(52, 7), holdem_grouped=grouped.legal_hands,
              unordered_seven_cards=unordered.legal_hands, internal_order_reduction=12,
              role_partitions_per_seven_card_set=420, mean_rank=grouped.mean_rank,
              rank_distributions_equal=True)
(ROOT/'results/holdem_group_counts.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
