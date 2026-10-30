import argparse,csv,json
from math import sqrt
from pathlib import Path
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--dictionary',type=Path,default=root/'data/processed/seven_card_dictionary');parser.add_argument('--output',type=Path,default=root/'results/nine_player_preflop_20261030');args=parser.parse_args()
p=args.output
with (p/'nine_player_preflop.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
independent=json.loads((p/'independent_rejection.json').read_text(encoding='utf-8'))
for check in independent:
    row=next(r for r in rows if r['hand']==check['hand'] and r['model']=='tight')
    check['importance_equity']=float(row['equity'])
    check['importance_se']=float(row['se'])
    check['combined_abs_z']=abs(check['equity']-check['importance_equity'])/sqrt(check['se']**2+check['importance_se']**2)
    assert check['combined_abs_z']<5
with SevenCardRankDictionary(args.dictionary) as table:
    check=table.relative_strength('6s 5s',[],['random']*8,samples=20000,seed=20261121)
row=next(r for r in rows if r['hand']=='65s' and r['model']=='random')
z=abs(check.equity-float(row['equity']))/sqrt(check.equity_standard_error**2+float(row['se'])**2)
assert z<5
report=dict(status='passed',full_joint_rejection=independent,random_api={'hand':'65s','samples':20000,'equity':check.equity,'se':check.equity_standard_error,'combined_abs_z':z},smallest_ess=min(float(r['effective_sample_size']) for r in rows if r['model']=='tight'))
(p/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
