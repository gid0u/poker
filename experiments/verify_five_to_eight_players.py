"""Independent whole-joint rejection checks for selected 5/8-player cases."""
import argparse,csv,json
from pathlib import Path
from math import comb,sqrt
import numpy as np
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import card_id
from multiway_preflop_examples import sample
from nine_player_preflop import calculate

def main():
 p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=5000);args=p.parse_args()
 with (args.output/'new_5_to_8.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
 assert len(rows)==88
 vals=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
 pool=np.array([[card_id(c) for c in h.cards] for h in parse_range('99+,AQs+,AKo')],dtype=np.uint8);checks=[]
 for i,(hand,model,players) in enumerate((('AA','random',4),('65s','tight',4),('AA','tight',7),('65s','tight',7))):
  row=next(r for r in rows if r['hand']==hand and r['model']==model and int(r['opponents'])==players)
  hero=[card_id(c) for c in row['hero'].split()];share,_,_=sample(np.random.default_rng(20261106+i),hero,args.samples,players,None if model=='random' else pool,vals,choose)
  value=float(share.mean());se=float(share.std(ddof=1)/sqrt(len(share)));combined=sqrt(se**2+float(row['se'])**2);z=abs(value-float(row['equity']))/combined
  assert z<5
  checks.append(dict(hand=hand,model=model,participants=players+1,rejection_equity=value,rejection_se=se,main_equity=float(row['equity']),combined_abs_z=z))
  print(json.dumps(checks[-1]),flush=True)
 row=next(r for r in rows if r['hand']=='AA' and r['model']=='random' and int(r['participants'])==5)
 hero=[card_id(c) for c in row['hero'].split()]
 share,_,_=sample(np.random.default_rng(20261120),hero,50000,4,None,vals,choose)
 value=float(share.mean());se=float(share.std(ddof=1)/sqrt(len(share)));z=abs(value-float(row['equity']))/sqrt(se**2+float(row['se'])**2)
 assert z<5
 checks.append(dict(hand='AA',model='random',participants=5,rejection_equity=value,rejection_se=se,main_equity=float(row['equity']),combined_abs_z=z,samples=50000,reason='higher-precision follow-up after 5000-sample check'))
 print(json.dumps(checks[-1]),flush=True)
 hero=[card_id('6s'),card_id('5s')]
 a=calculate(np.random.default_rng(77),hero,1000,pool,vals,choose)
 b=calculate(np.random.default_rng(77),hero,1000,pool,vals,choose,players=8)
 assert a==b
 report=dict(status='passed',conditions=len(rows),checks=checks,default_9_player_sampler_matches_explicit=True,
   min_strict_ess=min(float(r['effective_sample_size']) for r in rows if r['model']=='tight'))
 (args.output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
