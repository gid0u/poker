"""Postflop grouped holdout study. Exact ranks, independent MC labels/features."""
import argparse,csv,hashlib,json,time
from itertools import combinations,permutations
from math import comb,sqrt
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
from poker_evaluator.cards import Card
from poker_evaluator.evaluate5 import evaluate5
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary,card_id
from preflop_random_equity import lookup,draw_distinct

PERMS=list(permutations(range(4)))
TEXTURES=('paired','monotone','twotone_connected','twotone_other','rainbow')
TIGHT='99+,AQs+,AKo';PROXY='QQ+,AK'

def canonical(board):return min(tuple(sorted(4*(c//4)+p[c%4] for c in board)) for p in PERMS)
def texture(board):
    ranks=[x//4 for x in board];suits=[x%4 for x in board]
    if len(set(ranks))<3:return 'paired'
    if len(set(suits))==1:return 'monotone'
    if len(set(suits))==2:return 'twotone_connected' if max(ranks)-min(ranks)<=4 else 'twotone_other'
    return 'rainbow'
def cards_text(ids):return ' '.join('23456789TJQKA'[int(c)//4]+'schd'[int(c)%4] for c in ids)
def pool(notation):return np.array([[card_id(c) for c in hand.cards] for hand in parse_range(notation)],dtype=np.uint8)
def allowed(p,blocked):return p[~np.isin(p,blocked).any(axis=1)]
def moments(a):return float(np.mean(a)),float(np.var(a))
def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def board_sample(rng,deck,opps,n):
    """Sample opponent first, then uniform board; all positions are legal."""
    if opps is None:
        picks=draw_distinct(rng,n,size=4,deck_size=len(deck));return deck[picks[:,:2]],deck[picks[:,2:]]
    mapping={int(c):i for i,c in enumerate(deck)}
    pos=np.array([[mapping[int(c)] for c in h] for h in opps],dtype=np.uint8)
    used=np.empty((n,4),dtype=np.uint8);used[:,:2]=pos[rng.integers(0,len(pos),size=n)]
    for j in (2,3):
        used[:,j]=rng.integers(0,len(deck),size=n)
        clash=(used[:,:j]==used[:,j:j+1]).any(axis=1)
        while clash.any():
            used[clash,j]=rng.integers(0,len(deck),size=int(clash.sum()))
            clash=(used[:,:j]==used[:,j:j+1]).any(axis=1)
    return deck[used[:,:2]],deck[used[:,2:]]
def sample_equity(rng,hero,flop,deck,opps,n,values,choose):
    enemy,runout=board_sample(rng,deck,opps,n)
    a=np.empty((n,7),dtype=np.uint8);a[:,:2]=hero;a[:,2:5]=flop;a[:,5:]=runout
    b=np.empty((n,7),dtype=np.uint8);b[:,:2]=enemy;b[:,2:5]=flop;b[:,5:]=runout
    ours=lookup(a,values,choose);theirs=lookup(b,values,choose)
    share=(ours<theirs).astype(float)+.5*(ours==theirs)
    return float(share.mean()),float(share.std(ddof=1)/sqrt(n))
def proxy_distribution(rng,hero,flop,deck,opps,n,values,choose):
    _,runouts=board_sample(rng,deck,opps,n);qs=[]
    for a,b in runouts:
        legal=allowed(opps,[a,b]);final=list(flop)+[a,b]
        h=lookup(np.array([list(hero)+final],dtype=np.uint8),values,choose)[0]
        hands=np.empty((len(legal),7),dtype=np.uint8);hands[:,:2]=legal;hands[:,2:]=final
        other=lookup(hands,values,choose)
        qs.append(float(np.mean((h<other)+.5*(h==other))))
    return [float(np.mean(qs)),float(np.var(qs)),*[float(x) for x in np.quantile(qs,[.1,.5,.9])]]
def exact_equity(hero,flop,opps,values,choose):
    deck=[c for c in range(52) if c not in set(hero+flop)];total=0;share2=0
    for a,b in combinations(deck,2):
        final=flop+[a,b]
        legal=allowed(opps,[a,b])
        if not len(legal):continue
        own=lookup(np.array([hero+final],dtype=np.uint8),values,choose)[0]
        hands=np.empty((len(legal),7),dtype=np.uint8);hands[:,:2]=legal;hands[:,2:]=final
        other=lookup(hands,values,choose);total+=len(legal);share2+=2*int((own<other).sum())+int((own==other).sum())
    return share2/(2*total),total

def model_features(rows,level):
    arr=[]
    for r in rows:
        m=float(r['rank_mean'])/1000;v=float(r['rank_variance'])/1e6
        x=[m,m*m]
        if level>=2:x += [v,v*v,m*v]
        if level>=3:
            x += [float(r[k]) for k in ('board_high','board_low','board_span','board_suit_max','board_unique_ranks','hand_category','hero_high','hero_low','hero_suited')]
        if level>=4:x += [float(r['proxy_mean'])]
        if level>=5:x += [float(r[k]) for k in ('proxy_variance','proxy_q10','proxy_q50','proxy_q90')]
        arr.append(x)
    return np.asarray(arr,dtype=float)
def fit_predict(x,y,weights,train,test):
    center=np.average(x[train],axis=0,weights=weights[train]);scale=np.sqrt(np.average((x[train]-center)**2,axis=0,weights=weights[train]));scale[scale<1e-12]=1
    z=np.clip((x-center)/scale,-20,20);z=np.column_stack([np.ones(len(x)),z]);w=weights[train]/np.mean(weights[train]);ridge=np.eye(z.shape[1])*2;ridge[0,0]=0
    coef=np.linalg.solve(z[train].T@(w[:,None]*z[train])+ridge,z[train].T@(w*y[train]))
    return np.clip(z[test]@coef,0,1)
def summarize(y,p,w,se):
    d=p-y;return dict(n=len(y),rmse_pp=100*sqrt(np.average(d*d,weights=w)),mae_pp=100*np.average(abs(d),weights=w),max_abs_pp=100*max(abs(d)),label_mc_noise_pp=100*sqrt(np.average(se*se,weights=w)))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dictionary',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--boards-per-stratum',type=int,default=120);ap.add_argument('--hands-per-board',type=int,default=4);ap.add_argument('--samples',type=int,default=10000);ap.add_argument('--proxy-boards',type=int,default=64);args=ap.parse_args()
    assert args.samples>=2 and args.proxy_boards>=2 and 0<args.boards_per_stratum<=174
    args.output.mkdir(parents=True,exist_ok=True);start=time.time()
    config=dict(seed=20261031,board_strata=list(TEXTURES),boards_per_stratum=args.boards_per_stratum,hands_per_board=args.hands_per_board,samples_per_target=args.samples,independent_proxy_boards=args.proxy_boards,
        target_ranges={'random':'random','tight':TIGHT},proxy_range=PROXY,split='canonical suit-isomorphic flop, 75% train / 25% test stratified; additionally hold out all monotone boards',
        rank_features='exact over C(47,2) boards without opponent conditioning',labels='independent opponent-first Monte Carlo, same sampled completed board for hero and opponent',
        proxy='independent QQ+,AK board samples, exact legal opponent enumeration per sampled board',
        weight='orbit size * number of canonical boards in stratum / sampled canonical boards; uniform sampled hero per board',
        modeling='ridge alpha=2, train-only standardization, clipped to [0,1], fixed nested feature sets',
        limitations='finite random board and hero sample; group holdout not direct proof of generalization to new opponent ranges; conditional target MC errors')
    (args.output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    groups={}
    for b in combinations(range(52),3):
        k=canonical(b);groups[k]=groups.get(k,0)+1
    by=defaultdict(list)
    for board,orbit in sorted(groups.items()):by[texture(board)].append((board,orbit))
    assert len(groups)==1755 and sum(groups.values())==comb(52,3)
    rng=np.random.default_rng(20261031);selected=[]
    for name in TEXTURES:
        candidates=by[name];chosen=rng.choice(len(candidates),size=args.boards_per_stratum,replace=False)
        for i in chosen:selected.append((name,*candidates[int(i)],len(candidates)))
    selected=sorted(selected,key=lambda x:(x[0],x[1]))
    # Split at the complete board-orbit level, independently within each stratum.
    test_boards=set()
    for name in TEXTURES:
        choices=[s[1] for s in selected if s[0]==name]
        for i in rng.choice(len(choices),size=max(1,len(choices)//4),replace=False):test_boards.add(choices[int(i)])
    values=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
    tight=pool(TIGHT);proxy=pool(PROXY);seed_seq=np.random.SeedSequence(20261031).spawn(len(selected)*args.hands_per_board);rows=[]
    for idx,(name,board,orbit,group_count) in enumerate(selected):
        deck0=np.array([c for c in range(52) if c not in board],dtype=np.uint8)
        # Sample distinct hole combinations uniformly, independently of suit labels.
        hole_options=np.array(list(combinations(deck0,2)),dtype=np.uint8)
        hole_idx=rng.choice(len(hole_options),size=args.hands_per_board,replace=False)
        for j in hole_idx:
            hero=hole_options[int(j)];deck=np.array([c for c in deck0 if c not in hero],dtype=np.uint8)
            local=np.random.default_rng(seed_seq[len(rows)]);streams=local.integers(0,2**63,size=3)
            legal_tight=allowed(tight,list(hero)+list(board));legal_proxy=allowed(proxy,list(hero)+list(board))
            runouts=np.array(list(combinations(deck,2)),dtype=np.uint8);hands=np.empty((len(runouts),7),dtype=np.uint8);hands[:,:2]=hero;hands[:,2:5]=board;hands[:,5:]=runouts
            ranks=lookup(hands,values,choose);rm,rv=moments(ranks)
            yr,sr=sample_equity(np.random.default_rng(streams[0]),hero,board,deck,None,args.samples,values,choose)
            yt,st=sample_equity(np.random.default_rng(streams[1]),hero,board,deck,legal_tight,args.samples,values,choose)
            pm,pv,p10,p50,p90=proxy_distribution(np.random.default_rng(streams[2]),hero,board,deck,legal_proxy,args.proxy_boards,values,choose)
            br=[int(c)//4+2 for c in board];hr=sorted((int(c)//4+2 for c in hero),reverse=True);suits=[int(c)%4 for c in board]
            cat=evaluate5([Card(int(c)//4+2,int(c)%4) for c in list(hero)+list(board)])[0]
            rows.append(dict(board=cards_text(board),hero=cards_text(hero),group='-'.join(map(str,board)),texture=name,split='test' if board in test_boards else 'train',orbit_size=orbit,weight=orbit*group_count/args.boards_per_stratum,
                rank_mean=rm,rank_variance=rv,board_high=max(br),board_low=min(br),board_span=max(br)-min(br),board_suit_max=max(Counter(suits).values()),board_unique_ranks=len(set(br)),hand_category=cat,hero_high=hr[0],hero_low=hr[1],hero_suited=int(hero[0]%4==hero[1]%4),
                proxy_mean=pm,proxy_variance=pv,proxy_q10=p10,proxy_q50=p50,proxy_q90=p90,random_equity=yr,random_se=sr,tight_equity=yt,tight_se=st,legal_tight=len(legal_tight),legal_proxy=len(legal_proxy)))
        if (idx+1)%60==0:print(f'{idx+1}/{len(selected)} board groups, {len(rows)} states ({time.time()-start:.1f}s)',flush=True)
    write_csv(args.output/'states.csv',rows)
    # Test-board groups are disjoint before all feature construction and model fitting.
    assert not ({r['group'] for r in rows if r['split']=='test'} & {r['group'] for r in rows if r['split']=='train'})
    models=['mean','mean_variance','board','opponent_proxy','proxy_distribution'];weights_all={'class':np.ones(len(rows)),'population':np.array([r['weight'] for r in rows])}
    metrics=[];predictions=[]
    for split in ('group_holdout','monotone_holdout'):
        train=np.array([r['split']=='train' if split=='group_holdout' else r['texture']!='monotone' for r in rows]);test=~train
        for target in ('random','tight'):
            y=np.array([r[target+'_equity'] for r in rows]);se=np.array([r[target+'_se'] for r in rows])
            for scheme,w in weights_all.items():
                for level,name in enumerate(models,1):
                    prediction=fit_predict(model_features(rows,level),y,w,train,test)
                    base=dict(split=split,target=target,weighting=scheme,model=name,**summarize(y[test],prediction,w[test],se[test]));metrics.append(base)
                    for k,p in zip(np.flatnonzero(test),prediction):
                        predictions.append(dict(split=split,target=target,weighting=scheme,model=name,board=rows[k]['board'],hero=rows[k]['hero'],texture=rows[k]['texture'],hand_category=rows[k]['hand_category'],weight=rows[k]['weight'],actual=float(y[k]),predicted=float(p),error=float(p-y[k])))
    write_csv(args.output/'metrics.csv',metrics);write_csv(args.output/'predictions.csv',predictions)
    # Frozen selection after exploratory evaluation, then exact verification of largest errors.
    chosen=[]
    for target in ('random','tight'):
        candidates=[r for r in predictions if r['split']=='group_holdout' and r['target']==target and r['weighting']=='population' and r['model']=='proxy_distribution']
        chosen.append(max(candidates,key=lambda r:abs(r['error'])))
    (args.output/'exact_selection.json').write_text(json.dumps(chosen,indent=2),encoding='utf-8')
    checks=[]
    for c in chosen:
        from poker_evaluator.seven_card_dictionary import card_id
        hero=[card_id(s) for s in c['hero'].split()];flop=[card_id(s) for s in c['board'].split()]
        available=[i for i in range(52) if i not in hero+flop]
        op=np.array(list(combinations(available,2)),dtype=np.uint8) if c['target']=='random' else allowed(tight,hero+flop)
        exact,n=exact_equity(hero,flop,op,values,choose)
        row=next(r for r in rows if r['hero']==c['hero'] and r['board']==c['board'])
        se=row[c['target']+'_se'];checks.append(dict(target=c['target'],hero=c['hero'],board=c['board'],sampled=c['actual'],exact=exact,standard_error=se,abs_z=abs(c['actual']-exact)/se,model_prediction=c['predicted'],exact_joint_deals=n))
    result=dict(states=len(rows),board_groups=len(selected),test_states=sum(r['split']=='test' for r in rows),stratum_group_counts={k:len(v) for k,v in by.items()},metrics=metrics,exact_checks=checks,elapsed_seconds=time.time()-start)
    (args.output/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()

