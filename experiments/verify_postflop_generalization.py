"""Validate grouping, reproduce metrics, bootstrap held-out board groups, cross-check exact cases."""
import argparse,csv,json,time
from collections import defaultdict
from itertools import combinations,permutations
from math import sqrt
from pathlib import Path
import numpy as np
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary,card_id
from postflop_generalization import canonical,texture,fit_predict,model_features
root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--directory',type=Path,default=root/'results/postflop_generalization_20261030')
parser.add_argument('--dictionary',type=Path,default=root/'data/processed/seven_card_dictionary')
args=parser.parse_args();d=args.directory
def read(name):
    with (d/name).open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
rows=read('states.csv');pred=read('predictions.csv');config=json.loads((d/'config.json').read_text())
def write(name,rows):
    with (d/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
assert len(rows)==2400
train={r['group'] for r in rows if r['split']=='train'};test={r['group'] for r in rows if r['split']=='test'}
assert not train&test and len(train)==450 and len(test)==150
for r in rows:
    board=tuple(card_id(c) for c in r['board'].split());hero=tuple(card_id(c) for c in r['hero'].split())
    assert len(set(board+hero))==5 and canonical(board)==board and texture(board)==r['texture']
    assert all(canonical(tuple(4*(c//4)+p[c%4] for c in board))==board for p in permutations(range(4)))
weights=np.array([float(r['weight']) for r in rows]);mask=np.array([r['split']=='train' for r in rows]);x=model_features(rows,5);y=np.array([float(r['tight_equity']) for r in rows])
p0=fit_predict(x,y,weights,mask,~mask);y2=y.copy();y2[~mask]+=3
assert np.allclose(p0,fit_predict(x,y2,weights,mask,~mask),rtol=0,atol=1e-12)
stats=[]
for target in ('random','tight'):
    data=[r for r in pred if r['split']=='group_holdout' and r['target']==target and r['weighting']=='population' and r['model']=='proxy_distribution']
    for field in ('texture','hand_category'):
        for category in sorted(set(r[field] for r in data)):
            group=[r for r in data if r[field]==category];w=np.array([float(r['weight']) for r in group]);err=np.array([float(r['error']) for r in group]);stats.append(dict(target=target,grouping=field,category=category,states=len(group),board_groups=len({r['board'] for r in group}),rmse_pp=100*sqrt(np.average(err**2,weights=w)),mae_pp=100*np.average(abs(err),weights=w),max_abs_pp=100*max(abs(err))))
write('subgroup_metrics.csv',stats)
rng=np.random.default_rng(20261101);boot=[]
for target in ('random','tight'):
    base=[r for r in pred if r['split']=='group_holdout' and r['target']==target and r['weighting']=='population']
    indexes={m:{(r['board'],r['hero']):r for r in base if r['model']==m} for m in ('board','opponent_proxy','proxy_distribution')}
    keys=list(indexes['board']);assert all(set(keys)==set(k) for k in indexes.values())
    by=defaultdict(list)
    for i,key in enumerate(keys):by[indexes['board'][key]['texture']].append(i)
    weights_=np.array([float(indexes['board'][key]['weight']) for key in keys]);errors={m:np.array([float(indexes[m][key]['error']) for key in keys]) for m in indexes}
    boards_by_texture=defaultdict(dict)
    for i,key in enumerate(keys):boards_by_texture[indexes['board'][key]['texture']].setdefault(key[0],[]).append(i)
    for a,b in (('board','opponent_proxy'),('opponent_proxy','proxy_distribution')):
        changes=[]
        for _ in range(1000):
            indices=[]
            for boards in boards_by_texture.values():
                groups=list(boards.values())
                for pick in rng.integers(0,len(groups),size=len(groups)):indices.extend(groups[int(pick)])
            ix=np.array(indices);w=weights_[ix]
            changes.append(100*(sqrt(np.average(errors[a][ix]**2,weights=w))-sqrt(np.average(errors[b][ix]**2,weights=w))))
        boot.append(dict(target=target,comparison=a+' minus '+b,mean_delta_pp=float(np.mean(changes)),ci_low_pp=float(np.quantile(changes,.025)),ci_high_pp=float(np.quantile(changes,.975)),resamples=1000,scope='conditional on fitted models and sampled MC labels; stratified board-cluster bootstrap'))
write('bootstrap_differences.csv',boot)
checks=json.loads((d/'results.json').read_text())['exact_checks']
for item in checks:
    print('Checking public API exact:',item['target'],item['hero'],item['board'],flush=True)
    with SevenCardRankDictionary(args.dictionary) as table:
        result=table.relative_strength(item['hero'],item['board'],['random' if item['target']=='random' else config['target_ranges']['tight']],mode='exact',max_candidates=2000000)
    assert abs(result.equity-item['exact'])<1e-9
result=dict(status='passed',states=len(rows),train_board_groups=len(train),test_board_groups=len(test),canonical_suit_checks=len(rows)*24,heldout_target_perturbation_invariant=True,exact_results_match_public_api=True,bootstrap=boot)
(d/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
