"""Nine players: exact uniform joint random or importance sampled tight ranges."""
import argparse,csv,json,time
from pathlib import Path
from math import comb,sqrt
import numpy as np
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import card_id
from preflop_random_equity import lookup,draw_distinct

HANDS={'AA':'As Ac','22':'2s 2c','55':'5s 5c','65s':'6s 5s','A9o':'As 9c','AKs':'As Ks','AKo':'As Kc','72o':'7s 2c','32o':'3s 2c','42s':'4s 2s','42o':'4s 2c'}
TIGHT='99+,AQs+,AKo'

def proposal(rng,hero,n,pool):
    deck=np.array([i for i in range(52) if i not in hero],dtype=np.uint8)
    if pool is None:
        draw=deck[draw_distinct(rng,n,size=21,deck_size=50)]
        return draw[:,:16].reshape(n,8,2),draw[:,16:],np.ones(n),n
    legal=pool[~np.isin(pool,hero).any(axis=1)];hands=np.empty((n,8,2),dtype=np.uint8);w=np.ones(n);live=np.ones(n,dtype=bool)
    for j in range(8):
        possible=np.ones((n,len(legal)),dtype=bool)
        if j:
            used=hands[:,:j].reshape(n,2*j)
            possible=~(legal[None,:,0,None]==used[:,None,:]).any(axis=2)&~(legal[None,:,1,None]==used[:,None,:]).any(axis=2)
        count=possible.sum(axis=1);live &= count>0;w*=count/len(legal)
        k=np.floor(rng.random(n)*np.maximum(count,1)).astype(int)
        chosen=(np.cumsum(possible,axis=1)>k[:,None]).argmax(axis=1)
        hands[:,j,:]=legal[chosen]
    opponents=hands[live];w=w[live];m=len(w)
    board=np.empty((m,5),dtype=np.uint8);used=opponents.reshape(m,16)
    for j in range(5):
        board[:,j]=deck[rng.integers(0,50,size=m)]
        bad=(used==board[:,j:j+1]).any(axis=1)
        if j:bad|=(board[:,:j]==board[:,j:j+1]).any(axis=1)
        while bad.any():
            board[bad,j]=deck[rng.integers(0,50,size=int(bad.sum()))]
            bad=(used==board[:,j:j+1]).any(axis=1)
            if j:bad|=(board[:,:j]==board[:,j:j+1]).any(axis=1)
    assert np.all([len(set(list(h.ravel())+list(b)))==21 for h,b in zip(opponents[:100],board[:100])])
    return opponents,board,w,n

def calculate(rng,hero,n,pool,values,choose):
    weighted_sum=weighted_square=weighted_w=weighted_w2=weighted_y2=weighted_w2y=0.;wins=ties=dead=0
    for start in range(0,n,10000):
        batch=min(10000,n-start);opponents,board,w,_=proposal(rng,hero,batch,pool);m=len(w);dead+=batch-m
        if not m:continue
        card=np.empty((m,7),dtype=np.uint8);card[:,:2]=hero;card[:,2:]=board;own=lookup(card,values,choose)
        allr=[]
        for j in range(8):
            card[:,:2]=opponents[:,j,:];allr.append(lookup(card,values,choose))
        rivals=np.stack(allr,axis=1);winner=(own[:,None]<=rivals).all(axis=1);number_tied=(own[:,None]==rivals).sum(axis=1)
        share=np.where(winner,1/(number_tied+1),0.)
        weighted_sum+=float(np.dot(w,share));weighted_w+=float(w.sum());weighted_w2+=float(np.dot(w,w))
        weighted_square+=float(np.dot(w*w,share*share));weighted_w2y+=float(np.dot(w*w,share))
        wins+=float(np.dot(w,winner&(number_tied==0)));ties+=float(np.dot(w,winner&(number_tied>0)))
    if weighted_w<=0:raise ValueError('No valid weighted deals')
    e=weighted_sum/weighted_w
    resid2=max(0.,weighted_square-2*e*weighted_w2y+e*e*weighted_w2)
    se=sqrt(n/(n-1)*resid2)/weighted_w
    return dict(equity=e,se=se,ci95_low=max(0.,e-1.96*se),ci95_high=min(1.,e+1.96*se),win_probability=wins/weighted_w,tie_probability=ties/weighted_w,proposals=n,zero_weight=dead,effective_sample_size=weighted_w**2/weighted_w2)

def main():
    p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=300000);args=p.parse_args()
    if args.samples<2:p.error('at least two samples required')
    args.output.mkdir(parents=True,exist_ok=True);start=time.time();values=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
    pool=np.array([[card_id(c) for c in h.cards] for h in parse_range(TIGHT)],dtype=np.uint8)
    seeds=np.random.SeedSequence(20261104).spawn(len(HANDS)*2);rows=[]
    for i,(hand,hero_text) in enumerate(HANDS.items()):
        hero=[card_id(c) for c in hero_text.split()]
        for j,model in enumerate(('random','tight')):
            out=calculate(np.random.default_rng(seeds[2*i+j]),hero,args.samples,None if model=='random' else pool,values,choose)
            rows.append(dict(hand=hand,hero=hero_text,opponents=8,participants=9,model=model,method='independent sampling' if model=='random' else 'self-normalized sequential importance sampling',**out))
        print(f'{hand}: random {rows[-2]["equity"]:.6f}, tight {rows[-1]["equity"]:.6f}, ESS {rows[-1]["effective_sample_size"]:.0f}',flush=True)
    with (args.output/'nine_player_preflop.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    meta=dict(seed=20261104,samples_each=args.samples,opponents=8,participants=9,range=TIGHT,hero=HANDS,
        random_method='uniform ordered sample without replacement',tight_method='sequential uniformly sample legal combos, weight by product of fraction of each prior still legal; normalize weights',
        board='uniform remaining 5 cards after all hole cards',equity='expected pot share including 1/k ties',
        interval='normal approximation; self-normalized importance sampling SE from weighted residuals; asymptotic, per hand',
        limits='all players reach showdown; no bet, fold, rake or side pots; self-normalized importance sampling may have finite-sample bias',elapsed_seconds=time.time()-start)
    (args.output/'metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps(meta,indent=2))
if __name__=='__main__':main()
