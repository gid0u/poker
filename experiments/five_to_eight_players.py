"""Estimate missing 5-8 player preflop results and merge with prior work."""
import argparse,csv,json,time
from pathlib import Path
from math import comb
import numpy as np
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import card_id
from nine_player_preflop import HANDS,TIGHT,calculate

def read(path):
 with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def main():
 p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=100000);args=p.parse_args()
 if args.samples<2:p.error('at least two proposals')
 root=Path(__file__).resolve().parents[1];args.output.mkdir(parents=True,exist_ok=True);start=time.time()
 vals=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
 pool=np.array([[card_id(c) for c in h.cards] for h in parse_range(TIGHT)],dtype=np.uint8)
 seeds=np.random.SeedSequence(20261105).spawn(len(HANDS)*8);new=[]
 for i,(hand,text) in enumerate(HANDS.items()):
  hero=[card_id(c) for c in text.split()]
  for model_index,model in enumerate(('random','tight')):
   for j,opponents in enumerate((4,5,6,7)):
    rng=np.random.default_rng(seeds[8*i+4*model_index+j])
    result=calculate(rng,hero,args.samples,None if model=='random' else pool,vals,choose,players=opponents)
    new.append(dict(hand=hand,hero=text,participants=opponents+1,opponents=opponents,model=model,method='sampling' if model=='random' else 'importance_sampling',**result))
  print(hand+' completed',flush=True)
 combined=[]
 for row in read(root/'results/multiway_preflop_examples_20261030/multiway_preflop.csv'):
  combined.append(dict(hand=row['hand'],hero=row['hero'],participants=int(row['opponents'])+1,opponents=int(row['opponents']),model=row['model'],method=row['method'],equity=float(row['equity']),se=float(row['se']),ci95_low=float(row['ci95_low']),ci95_high=float(row['ci95_high']),proposals=int(row['samples']),effective_sample_size='',win_probability=float(row['win_probability']),tie_probability=float(row['tie_probability'])))
 for row in read(root/'results/nine_player_preflop_20261030/nine_player_preflop.csv'):
  combined.append(dict(hand=row['hand'],hero=row['hero'],participants=9,opponents=8,model=row['model'],method=row['method'],equity=float(row['equity']),se=float(row['se']),ci95_low=float(row['ci95_low']),ci95_high=float(row['ci95_high']),proposals=int(row['proposals']),effective_sample_size=float(row['effective_sample_size']),win_probability=float(row['win_probability']),tie_probability=float(row['tie_probability'])))
 combined.extend({k:r[k] for k in combined[0]} for r in new)
 combined.sort(key=lambda r:(list(HANDS).index(r['hand']),r['model'],r['participants']))
 assert len(new)==88 and len(combined)==176
 for name,data in [('new_5_to_8.csv',new),('all_2_to_9.csv',combined)]:
  with (args.output/name).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 metadata=dict(seed=20261105,participants=[5,6,7,8],new_conditions=len(new),proposals_per_condition=args.samples,opponent_range=TIGHT,
   model='uniform random or independently weighted strict ranges conditioned jointly on no overlap',
   strict_estimator='self-normalized sequential importance sampling; finite-sample bias possible',
   uncertainty='individual 95% normal approximation based on weighted residuals; not simultaneous',
   baseline='prior results for 2-4 and 9 participants; sample counts differ',
   caveat='all players reach showdown; no fold/betting/side pots; conditional distributions differ with number of players',elapsed_seconds=time.time()-start)
 (args.output/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8');print(json.dumps(metadata,indent=2),flush=True)
if __name__=='__main__':main()
