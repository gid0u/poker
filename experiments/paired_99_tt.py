"""Rank-swap paired importance analysis of 99 vs TT in the nine-player range model."""
import argparse,csv,json,time
from pathlib import Path
from math import comb,sqrt
import numpy as np
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import card_id
from nine_player_preflop import proposal
from preflop_random_equity import lookup

RANGE='99+,AQs+,AKo'
def swap(a):
    a=np.asarray(a);return np.where((a>=28)&(a<32),a+4,np.where((a>=32)&(a<36),a-4,a)).astype(np.uint8)
def score(hero,opponents,board,values,choose):
    n=len(board);cards=np.empty((n,7),dtype=np.uint8);cards[:,:2]=hero;cards[:,2:]=board;own=lookup(cards,values,choose);rivals=[]
    for i in range(8):
        cards[:,:2]=opponents[:,i,:];rivals.append(lookup(cards,values,choose))
    rivals=np.stack(rivals,axis=1);won=(own[:,None]<=rivals).all(axis=1);tie=(own[:,None]==rivals).sum(axis=1)
    return np.where(won,1/(tie+1),0.),won,tie

def main():
    p=argparse.ArgumentParser();p.add_argument('--dictionary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--samples',type=int,default=2000000);args=p.parse_args()
    if args.samples<2:p.error('at least 2 samples')
    args.output.mkdir(parents=True,exist_ok=True);start=time.time()
    pool=np.array([[card_id(c) for c in h.cards] for h in parse_range(RANGE)],dtype=np.uint8)
    unordered=lambda arr:{tuple(sorted(int(x) for x in row)) for row in arr}
    assert unordered(pool)==unordered(swap(pool)), 'Range must be invariant under 9/T rank swap'
    hero=[card_id('9s'),card_id('9c')];mapped=swap(hero).tolist()
    assert mapped==[card_id('Ts'),card_id('Tc')]
    values=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r');choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
    config=dict(seed=20261125,proposals=args.samples,hero99='9s 9c',heroTT='Ts Tc',opponents=8,range=RANGE,
        method='sample 99 deal via joint-corrected sequential importance, swap all 9 and T cards to get a TT deal; compare paired shares',
        symmetry='range maps bijectively to itself under 9/T permutation; uniform combo weights and legal deck preserve probability',
        interval='weighted paired residual standard error, normal approximation; board-group intervals are individual and descriptive',
        caveat='finite-sample self-normalized bias; fixed range assumptions; not exhaustive enumeration')
    (args.output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    rng=np.random.default_rng(20261125);sumw=sumw2=sa=sb=sd=sd2w2=sdw2=0.;group=np.zeros((4,5));counts=np.zeros(4,dtype=np.int64);oppcount=np.zeros(7);outcomes=np.zeros((3,3));dead=0;chunks=[]
    for start_at in range(0,args.samples,10000):
        n=min(10000,args.samples-start_at);opponents,board,w,_=proposal(rng,hero,n,pool,8);m=len(w);dead+=n-m
        a,aw,at=score(hero,opponents,board,values,choose);b,bw,bt=score(mapped,swap(opponents),swap(board),values,choose);delta=a-b
        sumw+=float(w.sum());sumw2+=float(w@w);sa+=float(w@a);sb+=float(w@b);sd+=float(w@delta);sd2w2+=float((w*w)@(delta*delta));sdw2+=float((w*w)@delta)
        nine=((board//4)==7).any(axis=1);ten=((board//4)==8).any(axis=1);idx=nine.astype(int)+2*ten.astype(int)
        for k in range(4):
            mask=idx==k;ww=w*mask;group[k]+=np.array([ww.sum(),ww@delta,(ww*ww)@delta,(ww*ww)@(delta*delta),mask.sum()]);counts[k]+=int(mask.sum())
        for k,rank in enumerate((7,8,9,10,11,12)):
            both=(opponents//4==rank).all(axis=2);oppcount[k]+=float(w@both.sum(axis=1))
        ak=((opponents//4==12).any(axis=2)&(opponents//4==11).any(axis=2)).sum(axis=1);oppcount[6]+=float(w@ak)
        ai=np.where(aw,np.where(at==0,2,1),0);bi=np.where(bw,np.where(bt==0,2,1),0)
        for x in range(3):
            for y in range(3):outcomes[x,y]+=float(w@((ai==x)&(bi==y)))
        if (start_at+n)%250000==0:print(f'{start_at+n}/{args.samples}, running paired gap={(sd/sumw):.6%}, elapsed {time.time()-start:.1f}s',flush=True)
    d=sd/sumw;res=max(0.,sd2w2-2*d*sdw2+d*d*sumw2);se=sqrt(args.samples/(args.samples-1)*res)/sumw
    groups=[]
    labels=['neither','9 only','T only','both']
    for i in range(4):
        sw,sdg,sw2d,sw2d2,_=group[i];contribution=sdg/sumw
        residual=max(0.,sw2d2-2*contribution*sw2d+contribution**2*sumw2)
        sg=sqrt(args.samples/(args.samples-1)*residual)/sumw
        groups.append(dict(board_group=labels[i],probability=sw/sumw,conditional_mean_difference=sdg/sw if sw else None,contribution=contribution,contribution_se=sg,ci95_low=contribution-1.96*sg,ci95_high=contribution+1.96*sg,sample_count=int(counts[i])))
    assert abs(sum(x['contribution'] for x in groups)-d)<1e-12
    result=dict(method='paired self-normalized importance sampling',proposals=args.samples,zero_weight=dead,effective_sample_size=sumw**2/sumw2,
        equity99=sa/sumw,equityTT=sb/sumw,difference_99_minus_TT=d,paired_se=se,paired_ci95=[d-1.96*se,d+1.96*se],
        opponent_pair_counts_99_scenario=dict(zip(('99','TT','JJ','QQ','KK','AA','AK'),(oppcount/sumw).tolist())),
        outcome_transition_matrix_99_rows_TT_columns=(outcomes/sumw).tolist(),outcome_categories=['loss','tie','sole_win'],
        board_group_decomposition=groups,elapsed_seconds=time.time()-start)
    (args.output/'paired_results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (args.output/'board_group_decomposition.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=groups[0].keys());w.writeheader();w.writerows(groups)
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
