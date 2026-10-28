from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary

results = []
with SevenCardRankDictionary() as table:
    for label, hero, board, opponents, mode in (
        ('AA vs QQ river', 'As Ah', 'Ks 8h 7d 3c 2s', ['QQ'], 'exact'),
        ('AA vs KK river', 'As Ah', 'Ks 8h 7d 3c 2s', ['KK'], 'exact'),
        ('AA vs KK,QQ river', 'As Ah', 'Ks 8h 7d 3c 2s', ['KK,QQ'], 'exact'),
        ('AA vs KK turn', 'As Ah', 'Ks 8h 7d 3c', ['KK'], 'exact'),
        ('AA vs KK turn sampled', 'As Ah', 'Ks 8h 7d 3c', ['KK'], 'sampling'),
        ('Royal board three-way', '2c 3d', 'As Ks Qs Js Ts', ['44', '66'], 'exact'),
    ):
        result = table.relative_strength(hero, board, opponents, mode=mode, samples=10000, seed=42)
        results.append(dict(label=label, **asdict(result)))
        print(f'{label}: mean={result.mean_rank:.4f}, var={result.variance_rank:.4f}, win={result.win_probability:.4%}, equity={result.equity:.4%}')
(ROOT/'results/relative_strength_examples.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
