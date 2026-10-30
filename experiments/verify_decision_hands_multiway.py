"""Independent full-joint rejection verification for sampled decision hands."""
import argparse,csv,json
from math import comb,sqrt
from pathlib import Path
import numpy as np
from poker_evaluator.seven_card_dictionary import card_id
from poker_evaluator.range_parser import parse_range
from multiway_preflop_examples import sample

def main():
 p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=6000);args=p.parse_args()
 with (args.output/'new_hands.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 assert len(rows)==154
 vals=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
 pool=np.array([[card_id(c) for c in h.cards] for h in parse_range('99+,AQs+,AKo')],dtype=np.uint8);checks=[]
 for i,(hand,model,players) in enumerate((('JTs','tight',8),('JJ','tight',8),('A5s','random',5),('KQo','tight',4),('44','random',2))):
  row=next(r for r in rows if r['hand']==hand and r['model']==model and int(r['opponents'])==players)
  hero=[card_id(c) for c in row['hero'].split()]
  shares,_,_=sample(np.random.default_rng(20261109+i),hero,args.samples,players,None if model=='random' else pool,vals,choose)
  e=float(shares.mean());se=float(shares.std(ddof=1)/sqrt(len(shares)));z=abs(e-float(row['equity']))/sqrt(se**2+float(row['se'])**2)
  assert z<5
  checks.append(dict(hand=hand,model=model,participants=players+1,verification_equity=e,verification_se=se,main_equity=float(row['equity']),combined_abs_z=z,samples=len(shares)))
  print(json.dumps(checks[-1]),flush=True)
 result=dict(status='passed',new_conditions=len(rows),checks=checks,min_strict_ess=min(float(r['effective_sample_size']) for r in rows if r['model']=='tight'),criterion='less than 5 combined standard errors, not a 95% coverage or equivalence proof')
 (args.output/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
