"""Independent whole-deal rejection check of the weighted paired simulation."""
import argparse
import json
from math import comb, sqrt
from pathlib import Path
import numpy as np
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import card_id
from multiway_preflop_examples import sample

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/rigorous_99_tt_20261030'
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dictionary',type=Path,required=True)
    args=parser.parse_args()
    pool=np.array([[card_id(c) for c in h.cards] for h in parse_range('99+,AQs+,AKo')],dtype=np.uint8)
    values=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r')
    choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
    rows={}
    for label,hero,seed in [('99','9s 9c',20261126),('TT','Ts Tc',20261127)]:
        shares, wins, ties=sample(np.random.default_rng(seed),[card_id(c) for c in hero.split()],50000,8,pool,values,choose)
        rows[label]={'samples':len(shares),'seed':seed,'equity':float(shares.mean()),'se':float(shares.std(ddof=1)/sqrt(len(shares))),'wins':wins,'ties':ties}
        print(label,rows[label],flush=True)
    diff=rows['99']['equity']-rows['TT']['equity']; se=sqrt(rows['99']['se']**2+rows['TT']['se']**2)
    paired=json.loads((OUT/'paired_results.json').read_text(encoding='utf-8'))
    z=abs(diff-paired['difference_99_minus_TT'])/sqrt(se**2+paired['paired_se']**2)
    result={'method':'independent full-joint rejection, 50000 accepted deals per hand','hands':rows,'difference':diff,'se':se,'ci95':[diff-1.96*se,diff+1.96*se],'combined_abs_z_vs_paired':z,'caveat':'normal approximation, independent random seeds; finite sampling uncertainty'}
    (OUT/'independent_rejection.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
    assert z < 5, 'Independent verification differs by more than five combined standard errors'
if __name__=='__main__':main()
