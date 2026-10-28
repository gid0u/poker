"""Monte Carlo HU preflop equity vs uniform random, with exact rank moments."""
import argparse
import csv
import json
import time
from math import comb, sqrt
from pathlib import Path
import numpy as np
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary, card_id
from poker_evaluator.rank_table import rank_seven_cards
from poker_evaluator.cards import Card


def draw_distinct(rng, count, size=7, deck_size=50):
    """Uniform ordered draws without replacement; each column rejects collisions."""
    cards = np.empty((count, size), dtype=np.uint8)
    for j in range(size):
        cards[:, j] = rng.integers(0, deck_size, size=count)
        if j:
            collision = (cards[:, :j] == cards[:, j:j+1]).any(axis=1)
            while collision.any():
                cards[collision, j] = rng.integers(0, deck_size, size=int(collision.sum()))
                collision = (cards[:, :j] == cards[:, j:j+1]).any(axis=1)
    return cards


def lookup(hands, values, choose):
    ordered = np.sort(hands, axis=1)
    index = np.zeros(len(hands), dtype=np.int64)
    for j in range(7):
        index += choose[j, ordered[:, j]]
    return values[index].astype(np.int64)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dictionary', type=Path, required=True)
    parser.add_argument('--moments', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--samples', type=int, default=1000000)
    parser.add_argument('--seed', type=int, default=20261028)
    args = parser.parse_args()
    if args.samples < 2:
        parser.error('samples must be at least two')
    args.output.mkdir(parents=True, exist_ok=True)
    source = list(csv.DictReader(args.moments.open(encoding='utf-8-sig')))
    assert len(source) == 169 and sum(int(r['combos']) for r in source) == 1326
    choose = np.array([[comb(c, k) for c in range(52)] for k in range(1, 8)], dtype=np.int64)
    values = np.memmap(args.dictionary/'seven_card_ranks.u16', dtype='<u2', mode='r')
    # Check vector lookup against the independent evaluator on random seven-card sets.
    checks = draw_distinct(np.random.default_rng(76), 128, deck_size=52)
    for hand, rank in zip(checks, lookup(checks, values, choose)):
        assert rank == rank_seven_cards(tuple(Card(int(c)//4+2, int(c)%4) for c in hand))
    assert np.all(lookup(checks, values, choose) == lookup(checks[:, ::-1], values, choose))
    seeds = np.random.SeedSequence(args.seed).spawn(169)
    started = time.time()
    rows = []
    for index, row in enumerate(source):
        hero = [card_id(c) for c in row['representative'].split()]
        deck = np.array([c for c in range(52) if c not in hero], dtype=np.uint8)
        rng = np.random.default_rng(seeds[index])
        wins = ties = losses = rank_sum = rank_square = 0
        for start in range(0, args.samples, 100000):
            count = min(100000, args.samples-start)
            cards = deck[draw_distinct(rng, count)]
            # First 2 cards are opponent; remaining 5 are the shared board.
            ours = np.empty((count, 7), dtype=np.uint8)
            ours[:, :2] = hero
            ours[:, 2:] = cards[:, 2:]
            a = lookup(ours, values, choose)
            b = lookup(cards, values, choose)
            wins += int((a < b).sum())
            ties += int((a == b).sum())
            losses += int((a > b).sum())
            rank_sum += int(a.sum())
            rank_square += int((a*a).sum())
        n = args.samples
        assert wins+ties+losses == n
        equity = (wins+ties/2)/n
        se = sqrt(max(0, (wins+ties/4)/n-equity**2)/(n-1))
        sample_mean = rank_sum/n
        # A random opponent does not change the marginal uniform board distribution.
        exact_variance = float(row['variance_rank'])
        z = (sample_mean-float(row['mean_rank']))/sqrt(exact_variance/n)
        assert abs(z) < 6, (row['hand'], z)
        rows.append(dict(hand=row['hand'],kind=row['kind'],representative=row['representative'],combos=int(row['combos']),
            mean_rank_exact=float(row['mean_rank']),variance_rank_exact=exact_variance,
            samples=n,wins=wins,ties=ties,losses=losses,win_probability=wins/n,tie_probability=ties/n,loss_probability=losses/n,
            equity=equity,equity_standard_error=se,equity_ci95_low=max(0,equity-1.96*se),equity_ci95_high=min(1,equity+1.96*se),
            sampled_mean_rank=sample_mean,sampled_variance_rank=(rank_square*n-rank_sum*rank_sum)/(n*n),rank_mean_z_check=z,
            seed_entropy=args.seed,seed_spawn_key=index))
        if (index+1)%13 == 0 or index==168:
            print(f'{index+1}/169 ({time.time()-started:.1f}s)', flush=True)
    for order, row in enumerate(sorted(rows,key=lambda r:r['equity'],reverse=True),1):
        row['estimated_equity_order'] = order
    with (args.output/'preflop_random_equity.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with SevenCardRankDictionary(args.dictionary) as table:
        sha=table.manifest['sha256']
    weighted_equity=sum(r['equity']*r['combos'] for r in rows)/1326
    weighted_se=sqrt(sum((r['combos']/1326*r['equity_standard_error'])**2 for r in rows))
    assert abs(weighted_equity-.5) < 6*weighted_se
    meta=dict(method='independent Monte Carlo, 169 SeedSequence child streams',seed=args.seed,samples_per_class=args.samples,total_samples=args.samples*169,
        hero='fixed real-card representative per suit-isomorphic class',board='unknown; 5 shared cards',opponent_count=1,opponent_range='uniform legal 2-card combo from remaining 50 cards',
        sampling='draw 7 distinct cards uniformly from remaining 50; first 2 opponent, last 5 board',equity='P(win)+P(tie)/2',
        confidence_interval='per-hand normal approximation 95%, not simultaneous across 169 hands',exact_joint_deals_per_class=comb(50,2)*comb(48,5),
        rank_moments='reused exact uniform C(50,5) moments; random opponent leaves board marginal unchanged',dictionary_sha256=sha,
        numpy_version=np.__version__,elapsed_seconds=time.time()-started,
        validation=dict(independent_rank_checks=128,max_abs_rank_mean_z=max(abs(r['rank_mean_z_check']) for r in rows),
            combo_weighted_equity=weighted_equity,combo_weighted_equity_se=weighted_se,expected_combo_weighted_equity=.5),
        limits='all players reach showdown; no fold, betting, rake; close estimated rankings can reverse within sampling error')
    (args.output/'run_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps(meta),flush=True)
    for r in rows:
        if r['hand'] in ('AA','KK','55','22','AKs','AKo','72o','32o'):
            print(r['hand'],r['equity'],r['equity_ci95_low'],r['equity_ci95_high'],flush=True)

if __name__ == '__main__':
    main()
