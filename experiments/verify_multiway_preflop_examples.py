import argparse,csv,json
from math import sqrt
from pathlib import Path
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary
root=Path(__file__).resolve().parents[1];d=root/'results/multiway_preflop_examples_20261030'
with (d/'multiway_preflop.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
checks=[]
parser=argparse.ArgumentParser();parser.add_argument('--dictionary',type=Path,default=root/'data/processed/seven_card_dictionary');args=parser.parse_args()
with SevenCardRankDictionary(args.dictionary) as table:
    for model in ('random','tight'):
        prior='random' if model=='random' else '99+,AQs+,AKo'
        row=next(r for r in rows if r['hand']=='65s' and r['model']==model and r['opponents']=='3')
        result=table.relative_strength('6s 5s',[],[prior]*3,samples=12000,seed=20261103)
        z=abs(result.equity-float(row['equity']))/sqrt(result.equity_standard_error**2+float(row['se'])**2)
        assert z<5
        checks.append(dict(model=model,opponents=3,samples=12000,api_equity=result.equity,combined_abs_z=z))
assert len(rows)==66 and all(float(r['ci95_low'])<=float(r['equity'])<=float(r['ci95_high']) for r in rows)
(d/'verification.json').write_text(json.dumps({'status':'passed','rows':len(rows),'checks':checks},indent=2),encoding='utf-8')
print(json.dumps(checks,indent=2))
