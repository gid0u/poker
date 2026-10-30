"""Multiway preflop showcase; independent opponent ranges jointly conditioned on legality."""
import argparse,csv,json,time
from math import comb,sqrt
from pathlib import Path
import numpy as np
from poker_evaluator.seven_card_dictionary import card_id,SevenCardRankDictionary
from poker_evaluator.range_parser import parse_range
from preflop_random_equity import lookup,draw_distinct

HANDS={'AA':'As Ac','22':'2s 2c','55':'5s 5c','65s':'6s 5s','A9o':'As 9c','AKs':'As Ks','AKo':'As Kc','72o':'7s 2c','32o':'3s 2c','42s':'4s 2s','42o':'4s 2c'}
TIGHT='99+,AQs+,AKo'

def sample(rng,hero,count,players,pool,values,choose):
    deck=np.array([i for i in range(52) if i not in hero],dtype=np.uint8)
    if pool is None:
        draw=deck[draw_distinct(rng,count,size=2*players+5,deck_size=50)]
        opponents=draw[:,:2*players].reshape(count,players,2);board=draw[:,2*players:]
    else:
        legal=pool[~np.isin(pool,hero).any(axis=1)]
        opponents=np.empty((count,players,2),dtype=np.uint8);accepted=0;attempts=0
        while accepted<count:
            n=max(1000,(count-accepted)*2)
            cards=legal[rng.integers(0,len(legal),size=(n,players))]
            flat=cards.reshape(n,2*players)
            valid=np.all(np.diff(np.sort(flat,axis=1),axis=1)!=0,axis=1)
            good=cards[valid][:count-accepted];opponents[accepted:accepted+len(good)]=good
            accepted+=len(good);attempts+=n
        # Draw the five public cards uniformly conditional on the whole deal.
        board=np.empty((count,5),dtype=np.uint8);used=opponents.reshape(count,2*players)
        for j in range(5):
            board[:,j]=deck[rng.integers(0,50,size=count)]
            bad=np.isin(board[:,j],hero) # hero absent from deck; retained for clarity
            bad|=(used==board[:,j:j+1]).any(axis=1)
            if j:bad|=(board[:,:j]==board[:,j:j+1]).any(axis=1)
            while bad.any():
                board[bad,j]=deck[rng.integers(0,50,size=int(bad.sum()))]
                bad=(used==board[:,j:j+1]).any(axis=1)
                if j:bad|=(board[:,:j]==board[:,j:j+1]).any(axis=1)
    our=np.empty((count,7),dtype=np.uint8);our[:,:2]=hero;our[:,2:]=board;our_rank=lookup(our,values,choose)
    ranks=[]
    for i in range(players):
        v=np.empty((count,7),dtype=np.uint8);v[:,:2]=opponents[:,i,:];v[:,2:]=board;ranks.append(lookup(v,values,choose))
    rival=np.stack(ranks,axis=1);winner=(our_rank[:,None]<=rival).all(axis=1);ties=(rival==our_rank[:,None]).sum(axis=1)
    shares=np.where(winner,1/(ties+1),0.0)
    return shares,int((winner&(ties==0)).sum()),int((winner&(ties>0)).sum())

def main():
    p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=300000);args=p.parse_args()
    if args.samples<2:p.error('at least two samples')
    args.output.mkdir(parents=True,exist_ok=True);start=time.time()
    base=Path(__file__).resolve().parents[1]/'results';random={r['hand']:r for r in csv.DictReader((base/'preflop_random_equity/preflop_random_equity.csv').open(encoding='utf-8-sig'))};tight={(r['hand'],r['opponent']):r for r in csv.DictReader((base/'opponent_range_comparison_20261030/preflop_comparison.csv').open(encoding='utf-8-sig'))}
    vals=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
    pool=np.array([[card_id(c) for c in h.cards] for h in parse_range(TIGHT)],dtype=np.uint8)
    seeds=np.random.SeedSequence(20261102).spawn(len(HANDS)*4);rows=[]
    for hand,text in HANDS.items():
        hero=[card_id(c) for c in text.split()]
        for model in ('random','tight'):
            old=random[hand] if model=='random' else tight[hand,'tight']
            rows.append(dict(hand=hand,hero=text,opponents=1,model=model,method='previous_sampling',samples=int(old['samples']),equity=float(old['equity']),se=float(old['equity_standard_error'] if model=='random' else old['equity_se']),win_probability=float(old['win_probability']),tie_probability=float(old['tie_probability'])))
            for n in (2,3):
                rng=np.random.default_rng(seeds[4*list(HANDS).index(hand)+(0 if model=='random' else 2)+(n-2)]);parts=[];wins=ties=0
                for start_at in range(0,args.samples,50000):
                    shares,w,t=sample(rng,hero,min(50000,args.samples-start_at),n,None if model=='random' else pool,vals,choose)
                    parts.append(shares);wins+=w;ties+=t
                shares=np.concatenate(parts);e=float(shares.mean());se=float(shares.std(ddof=1)/sqrt(len(shares)))
                rows.append(dict(hand=hand,hero=text,opponents=n,model=model,method='sampling',samples=len(shares),equity=e,se=se,win_probability=wins/len(shares),tie_probability=ties/len(shares)))
        print(hand+' completed',flush=True)
    for row in rows:
        row['ci95_low']=max(0.,row['equity']-1.96*row['se'])
        row['ci95_high']=min(1.,row['equity']+1.96*row['se'])
    with (args.output/'multiway_preflop.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with SevenCardRankDictionary(args.dictionary) as table:
        # Independent API implementation, weighted joint rejection, small verification sample.
        checks=[]
        for model in ('random','tight'):
            reference=next(r for r in rows if r['hand']=='65s' and r['model']==model and r['opponents']==2)
            result=table.relative_strength('6s 5s',[],['random' if model=='random' else TIGHT]*2,samples=10000,seed=631)
            z=abs(result.equity-reference['equity'])/sqrt(result.equity_standard_error**2+reference['se']**2)
            assert z<5
            checks.append(dict(model=model,equity=result.equity,combined_abs_z=z))
    config=dict(seed=20261102,samples_each=args.samples,hero=HANDS,opponent_counts=[1,2,3],opponent_models={'random':'uniform legal combinations','tight':TIGHT},
       measure='independent uniform opponent priors conditioned jointly on no card overlap; shared uniform board',
       equity='expected pot share; k-way tie = 1/k',assumption='all opponents reach showdown; no betting, rake or side pots',
       one_opponent='previous 1M random and 300k tight estimates',ci='normal approximation: equity +/- 1.96 standard error; per hand',checks=checks,elapsed_seconds=time.time()-start)
    (args.output/'run_metadata.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    print(json.dumps(config,indent=2))
if __name__=='__main__':main()
