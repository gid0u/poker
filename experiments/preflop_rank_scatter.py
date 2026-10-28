"""Exact preflop rank moments for 169 suit-isomorphic classes."""
import argparse,csv,json,time
from itertools import combinations,chain
from math import comb
from pathlib import Path
import numpy as np
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary,card_id

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dictionary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    started=time.time()
    n=comb(50,5)
    boards=np.fromiter(chain.from_iterable(combinations(range(50),5)),dtype=np.uint8,count=n*5).reshape(n,5)
    choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
    values=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r')
    rows=[]
    ranks='AKQJT98765432'
    for i,a in enumerate(ranks):
        for b in ranks[i:]:
            for kind in (('pair',) if a==b else ('suited','offsuit')):
                label=a+b+('' if a==b else 's' if kind=='suited' else 'o')
                hero=(a+'s',b+('s' if kind=='suited' else 'c'))
                ids=[card_id(c) for c in hero]
                deck=np.array([c for c in range(52) if c not in ids],dtype=np.uint8)
                total=square=0
                for start in range(0,n,100000):
                    board=deck[boards[start:start+100000]]
                    hands=np.empty((len(board),7),dtype=np.uint8)
                    hands[:,:5]=board; hands[:,5:]=ids
                    hands.sort(axis=1)
                    index=np.zeros(len(board),dtype=np.int64)
                    for k in range(7): index+=choose[k,hands[:,k]]
                    r=values[index].astype(np.int64)
                    total+=int(r.sum()); square+=int((r*r).sum())
                mean=total/n; variance=(square*n-total*total)/(n*n)
                rows.append(dict(hand=label,kind=kind,representative=' '.join(hero),combos=6 if a==b else 4 if kind=='suited' else 12,boards=n,rank_sum=total,rank_squared_sum=square,mean_rank=mean,variance_rank=variance,standard_deviation_rank=variance**.5))
        print(f'{a}: {len(rows)}/169 ({time.time()-started:.1f}s)',flush=True)
    with SevenCardRankDictionary(args.dictionary) as table:
        baseline=table.all_hands_statistics
        weighted_mean=sum(r['mean_rank']*r['combos'] for r in rows)/1326
        weighted_second=sum((r['variance_rank']+r['mean_rank']**2)*r['combos'] for r in rows)/1326
        assert abs(weighted_mean-baseline['mean_rank'])<1e-8
        assert abs(weighted_second-weighted_mean**2-baseline['variance_rank'])<1e-6
        # Independent public reader checks for vectorized combinadic indices.
        for label in ('AA','AKs','AKo','22'):
            row=next(r for r in rows if r['hand']==label)
            ids=[card_id(c) for c in row['representative'].split()]
            deck=[c for c in range(52) if c not in ids]
            for board in (deck[:5],deck[-5:]):
                hand=sorted(ids+board)
                idx=sum(comb(c,k) for k,c in enumerate(hand,1))
                assert int(values[idx])==table[hand]
    with (args.output/'preflop_rank_scatter.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    metadata=dict(method='exact enumeration',classes=169,physical_hole_combos=1326,boards_per_class=n,total_representative_boards=n*169,opponents=None,board_distribution='uniform C(remaining 50 cards,5)',variance='population variance of final 7-card rank',rank_order='1 strongest; 7462 weakest',baseline_mean=baseline['mean_rank'],baseline_variance=baseline['variance_rank'],dictionary_sha256=baseline['sha256'],weighted_mean_check=weighted_mean,weighted_variance_check=weighted_second-weighted_mean**2,elapsed_seconds=time.time()-started)
    (args.output/'preflop_rank_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    print(json.dumps(metadata),flush=True)
if __name__=='__main__': main()
