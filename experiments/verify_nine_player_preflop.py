"""Independent full-joint rejection check of weighted 9-player estimator."""
import argparse,csv,json
from pathlib import Path
from math import comb,sqrt
import numpy as np
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import card_id
from multiway_preflop_examples import sample

def main():
 p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=4000);args=p.parse_args()
 vals=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
 pool=np.array([[card_id(c) for c in h.cards] for h in parse_range('99+,AQs+,AKo')],dtype=np.uint8)
 checks=[]
 for i,(hand,text) in enumerate((('AA','As Ac'),('65s','6s 5s'))):
  hero=[card_id(c) for c in text.split()];shares,wins,ties=sample(np.random.default_rng(20261120+i),hero,args.samples,8,pool,vals,choose)
  e=float(shares.mean());se=float(shares.std(ddof=1)/sqrt(len(shares)))
  checks.append(dict(hand=hand,method='independent whole-joint rejection',samples=len(shares),equity=e,se=se))
  print(json.dumps(checks[-1]),flush=True)
 (args.output/'independent_rejection.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
if __name__=='__main__':main()
