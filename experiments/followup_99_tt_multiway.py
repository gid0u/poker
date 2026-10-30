"""Follow up exploratory 99/TT reversal using independent joint rejection."""
import argparse,csv,json
from pathlib import Path
from math import comb,sqrt
import numpy as np
from poker_evaluator.seven_card_dictionary import card_id
from poker_evaluator.range_parser import parse_range
from multiway_preflop_examples import sample
p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=20000);args=p.parse_args()
with (args.output/'new_hands.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
values=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
pool=np.array([[card_id(c) for c in h.cards] for h in parse_range('99+,AQs+,AKo')],dtype=np.uint8)
results=[]
for i,hand in enumerate(('99','TT')):
 r=next(r for r in rows if r['hand']==hand and r['model']=='tight' and int(r['participants'])==9)
 hero=[card_id(c) for c in r['hero'].split()]
 share,_,_=sample(np.random.default_rng(20261119+i),hero,args.samples,8,pool,values,choose)
 results.append(dict(hand=hand,hero=r['hero'],equity=float(share.mean()),se=float(share.std(ddof=1)/sqrt(len(share))),samples=len(share),primary_equity=float(r['equity']),primary_se=float(r['se'])))
 print(json.dumps(results[-1]),flush=True)
gap=results[0]['equity']-results[1]['equity'];se=sqrt(sum(r['se']**2 for r in results))
report=dict(method='independent whole-joint rejection',selection='99 vs TT selected after exploratory 9-player results; fresh draws',results=results,gap_99_minus_tt=gap,gap_ci95=[gap-1.96*se,gap+1.96*se],sign_confirmed=gap-1.96*se>0)
(args.output/'followup_99_tt.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
