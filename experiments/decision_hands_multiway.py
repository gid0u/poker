"""Extend prior multiway comparison to newly identified decision-sensitive hands."""
import argparse,csv,json,time
from math import comb
from pathlib import Path
import numpy as np
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import card_id
from nine_player_preflop import calculate

NEW=('33','44','99','TT','JJ','AQs','A5s','KQo','KQs','JTs','T9s')
TIGHT='99+,AQs+,AKo'
FIELDS=('hand','hero','participants','opponents','model','method','equity','se','ci95_low','ci95_high','proposals','effective_sample_size')

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=100000);args=p.parse_args()
    if args.samples<2:p.error('samples must be at least 2')
    root=Path(__file__).resolve().parents[1];args.output.mkdir(parents=True,exist_ok=True);started=time.time()
    prior=read(root/'results/five_to_eight_players_20261030/all_2_to_9.csv')
    one_random={r['hand']:r for r in read(root/'results/preflop_random_equity/preflop_random_equity.csv')}
    one_tight={(r['hand'],r['opponent']):r for r in read(root/'results/opponent_range_comparison_20261030/preflop_comparison.csv')}
    vals=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
    pool=np.array([[card_id(c) for c in h.cards] for h in parse_range(TIGHT)],dtype=np.uint8)
    seeds=np.random.SeedSequence(20261107).spawn(len(NEW)*14);new=[]
    for i,hand in enumerate(NEW):
        text=one_random[hand]['representative'];hero=[card_id(c) for c in text.split()]
        for j,model in enumerate(('random','tight')):
            for players in range(2,9):
                rng=np.random.default_rng(seeds[i*14+j*7+players-2])
                result=calculate(rng,hero,args.samples,None if model=='random' else pool,vals,choose,players=players)
                new.append(dict(hand=hand,hero=text,participants=players+1,opponents=players,model=model,method='independent_MC' if model=='random' else 'self_normalized_importance',**result))
        print(hand+' completed',flush=True)
    combined=[{k:r[k] for k in FIELDS} for r in prior]
    for hand in NEW:
        for model in ('random','tight'):
            row=one_random[hand] if model=='random' else one_tight[hand,'tight']
            equity=float(row['equity']);se=float(row['equity_standard_error'] if model=='random' else row['equity_se'])
            combined.append(dict(hand=hand,hero=row['representative'],participants=2,opponents=1,model=model,method='prior_MC',equity=equity,se=se,ci95_low=max(0,equity-1.96*se),ci95_high=min(1,equity+1.96*se),proposals=int(row['samples']),effective_sample_size=''))
    combined.extend({k:r[k] for k in FIELDS} for r in new)
    assert len(new)==len(NEW)*14 and len(combined)==(11+len(NEW))*16
    combined.sort(key=lambda r:(r['hand'],r['model'],int(r['participants'])))
    for name,data in [('new_hands.csv',new),('all_hands.csv',combined)]:
        with (args.output/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=data[0].keys());w.writeheader();w.writerows(data)
    meta=dict(new_hands=list(NEW),new_conditions=len(new),samples_per_condition=args.samples,seed=20261107,
        target='one to eight opponents; independent range priors jointly conditioned on no duplicate cards',
        tight=TIGHT,strict_method='self-normalized sequential importance sampling; asymptotic normal CI and potential finite-sample bias',
        random_method='uniform without replacement',prior='11 previously studied hands for 2-9 total participants; new hands heads-up reuse previous estimates',
        equity='expected share at showdown, ties split',limits='no betting, folds, rake, sidepots or behavioral inference',elapsed_seconds=time.time()-started)
    (args.output/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8');print(json.dumps(meta,indent=2),flush=True)
if __name__=='__main__':main()
