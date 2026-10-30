"""Compare fixed tight participation ranges with existing random-opponent research."""
import argparse,csv,json,time
from itertools import combinations
from math import comb,sqrt
from pathlib import Path
import numpy as np
from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary,card_id
from preflop_random_equity import lookup
from evaluate_preflop_hypotheses import cross_validate

RANGES={'tight':'99+,AQs+,AKo','ultra_tight':'QQ+,AK'}
def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def read_csv(path):return list(csv.DictReader(path.open(encoding='utf-8-sig')))
def idpool(value):return np.array([[card_id(c) for c in h.cards] for h in parse_range(value)],dtype=np.uint8)
def filter_pool(pool,blocked):return pool[~np.isin(pool,blocked).any(axis=1)]
def draw_board(rng,opponent_positions):
    n=len(opponent_positions);used=np.empty((n,7),dtype=np.uint8);used[:,:2]=opponent_positions
    for j in range(2,7):
        used[:,j]=rng.integers(0,50,size=n)
        bad=(used[:,:j]==used[:,j:j+1]).any(axis=1)
        while bad.any():
            used[bad,j]=rng.integers(0,50,size=int(bad.sum()))
            bad=(used[:,:j]==used[:,j:j+1]).any(axis=1)
    return used[:,2:]
def aggregate_states(records):
    # Board posterior mass is number of compatible range combos, NOT uniform.
    n=sum(r['opponent_combos'] for r in records)
    mu=sum(r['rank']*r['opponent_combos'] for r in records)/n
    vr=sum(r['opponent_combos']*(r['rank']-mu)**2 for r in records)/n
    e=sum(r['share_numerator'] for r in records)/(2*n)
    vq=sum(r['opponent_combos']*(r['equity']-e)**2 for r in records)/n
    return dict(rank_mean=mu,rank_variance=vr,equity=e,board_equity_variance=vq,joint_deals=n)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dictionary',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--samples',type=int,default=300000);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);root=Path(__file__).resolve().parents[1];started=time.time()
    random_pre=read_csv(root/'results/preflop_random_equity/preflop_random_equity.csv');random_flop=read_csv(root/'results/postflop_hypotheses_20261030/flop_states.csv');random_turn=read_csv(root/'results/postflop_hypotheses_20261030/turn_states.csv');random_river=read_csv(root/'results/postflop_hypotheses_20261030/river_states.csv')
    config=dict(ranges=RANGES,range_combo_counts={k:len(idpool(v)) for k,v in RANGES.items()},interpretation='fixed preflop participation; condition on opponent having entered; no later action filtering',weights='uniform legal physical combos within each range',preflop_samples_each=args.samples,seed=20261101,numpy_version=np.__version__,preflop_method='Monte Carlo',postflop_method='exact; board posterior reweighted by compatible opponent combo counts',reference_random='existing 1M/class preflop MC and exact 46/2162/49726 postflop panel',limits='no folds/blinds/bets/rake EV; hand chosen by fixed priors not inferred from actions; not an OCHS reproduction')
    (args.output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64);values=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r')
    pre=[]
    seeds=np.random.SeedSequence(20261101).spawn(2)
    for range_index,(label,notation) in enumerate(RANGES.items()):
        pool=idpool(notation);children=seeds[range_index].spawn(169)
        for index,row in enumerate(random_pre):
            hero=[card_id(c) for c in row['representative'].split()];deck=np.array([c for c in range(52) if c not in hero],dtype=np.uint8);reverse={int(c):i for i,c in enumerate(deck)}
            legal=filter_pool(pool,hero);positions=np.array([[reverse[int(c)] for c in h] for h in legal],dtype=np.uint8);rng=np.random.default_rng(children[index])
            wins=ties=rank_sum=rank_square=0
            for start in range(0,args.samples,100000):
                n=min(100000,args.samples-start);opponent=positions[rng.integers(0,len(positions),size=n)];board=deck[draw_board(rng,opponent)]
                ours=np.empty((n,7),dtype=np.uint8);ours[:,:2]=hero;ours[:,2:]=board
                villain=np.empty((n,7),dtype=np.uint8);villain[:,:2]=deck[opponent];villain[:,2:]=board
                a=lookup(ours,values,choose);b=lookup(villain,values,choose)
                wins+=int((a<b).sum());ties+=int((a==b).sum());rank_sum+=int(a.sum());rank_square+=int((a*a).sum())
            n=args.samples;e=(wins+ties/2)/n;se=sqrt(max(0,(wins+ties/4)/n-e*e)/(n-1))
            pre.append(dict(hand=row['hand'],representative=row['representative'],kind=row['kind'],combos=int(row['combos']),opponent=label,range_notation=notation,legal_opponent_combos=len(legal),samples=n,win_probability=wins/n,tie_probability=ties/n,equity=e,equity_se=se,ci95_low=e-1.96*se,ci95_high=e+1.96*se,random_equity=float(row['equity']),random_se=float(row['equity_standard_error']),equity_difference=e-float(row['equity']),conditional_rank_mean=rank_sum/n,conditional_rank_variance=(rank_square*n-rank_sum*rank_sum)/(n*n),random_rank_mean_exact=float(row['mean_rank_exact']),random_rank_variance_exact=float(row['variance_rank_exact'])))
            if (index+1)%26==0 or index==168:print(f'preflop {label}: {index+1}/169 ({time.time()-started:.1f}s)',flush=True)
    write_csv(args.output/'preflop_comparison.csv',pre)
    flops=[];turns=[];rivers=[];base_flop={(r['hero'],r['flop']):r for r in random_flop};base_turn={(r['hero'],r['board']):r for r in random_turn}
    for label,notation in RANGES.items():
        pool=idpool(notation)
        for row in random_flop:
            hero_text=row['hero'];flop_text=row['flop'];hero=[card_id(c) for c in hero_text.split()];flop=[card_id(c) for c in flop_text.split()];legal=filter_pool(pool,hero+flop)
            available=[c for c in range(52) if c not in hero+flop];by_turn={c:[] for c in available};records=[]
            # Reuse exact hero ranks and completed boards; recompute opponent ranks.
            source=[r for r in random_river if r['hero']==hero_text and r['flop']==flop_text]
            for saved in source:
                board=[card_id(c) for c in saved['board'].split()];a,b=board[-2:];opponents=filter_pool(legal,[a,b]);m=len(opponents)
                if not m:continue
                hands=np.empty((m,7),dtype=np.uint8);hands[:,:2]=opponents;hands[:,2:]=board
                enemy=lookup(hands,values,choose);rank=int(saved['rank']);k=2*int((rank<enemy).sum())+int((rank==enemy).sum())
                r=dict(hero=hero_text,flop=flop_text,board=saved['board'],opponent=label,rank=rank,opponent_combos=m,share_numerator=k,equity=k/(2*m),random_equity=float(saved['equity']))
                records.append(r);by_turn[a].append(r);by_turn[b].append(r);rivers.append(r)
            stats=aggregate_states(records);assert stats['joint_deals']==len(legal)*990
            record=dict(hero=hero_text,flop=flop_text,opponent=label,legal_opponent_combos=len(legal),**stats,random_equity=float(row['equity']),random_board_equity_variance=float(row['board_equity_variance']),random_rank_mean=float(row['rank_mean']),random_rank_variance=float(row['rank_variance']))
            flops.append(record)
            for c,entries in by_turn.items():
                if not entries:continue
                stats=aggregate_states(entries);count=len(filter_pool(legal,[c]));assert stats['joint_deals']==count*44
                board_text=' '.join([flop_text,'23456789TJQKA'[c//4]+'schd'[c%4]])
                baseline=base_turn[hero_text,board_text]
                turns.append(dict(hero=hero_text,flop=flop_text,board=board_text,opponent=label,legal_opponent_combos=count,**stats,random_equity=float(baseline['equity'])))
        print(f'postflop {label}: completed ({time.time()-started:.1f}s)',flush=True)
    write_csv(args.output/'flop_comparison.csv',flops);write_csv(args.output/'turn_comparison.csv',turns);write_csv(args.output/'river_comparison.csv',rivers)
    metrics=[];x=np.array([[float(r['mean_rank_exact']),float(r['variance_rank_exact'])] for r in random_pre]);groups=[r['hand'][:2] for r in random_pre]
    for opponent in ('random',*RANGES):
        y=np.array([float(r['equity']) for r in random_pre]) if opponent=='random' else np.array([r['equity'] for r in pre if r['opponent']==opponent])
        for weighting in ('class','combo'):
            weights=np.ones(169) if weighting=='class' else np.array([int(r['combos']) for r in random_pre])
            for name,use_var in [('mean_quadratic',False),('mean_variance_quadratic',True)]:
                pred=cross_validate(x,y,weights,groups,2,use_var)
                metrics.append(dict(opponent=opponent,weighting=weighting,model=name,rmse_pp=100*sqrt(np.average((pred-y)**2,weights=weights)),mae_pp=100*np.average(abs(pred-y),weights=weights)))
    write_csv(args.output/'prediction_metrics.csv',metrics)
    api_checks=[]
    with SevenCardRankDictionary(args.dictionary) as table:
        for label,notation in RANGES.items():
            for board in ('Ts 9s 2c','Qs Js 8s'):
                target=next(r for r in flops if r['opponent']==label and r['flop']==board and r['hero']=='As Ah')
                v=table.relative_strength('As Ah',board,[notation],mode='exact',max_candidates=100000)
                assert abs(v.equity-target['equity'])<1e-10 and abs(v.mean_rank-target['rank_mean'])<1e-7 and abs(v.variance_rank-target['rank_variance'])<1e-4
                api_checks.append(dict(opponent=label,hero='As Ah',board=board,joint_deals=v.outcomes,equity_error=abs(v.equity-target['equity'])))
            for h in ('55','AKs'):
                r=next(r for r in pre if r['opponent']==label and r['hand']==h)
                v=table.relative_strength(r['representative'],[],[notation],samples=30000,seed=20261102)
                z=abs(v.equity-r['equity'])/sqrt(v.equity_standard_error**2+r['equity_se']**2);assert z<5
                api_checks.append(dict(opponent=label,hand=h,samples=30000,combined_abs_z=z))
    summary={}
    for label in RANGES:
        selected=[r for r in pre if r['opponent']==label];post=[r for r in flops if r['opponent']==label]
        ordering_flips=0
        for a,b in combinations(selected,2):
            if (a['equity']-b['equity'])*(a['random_equity']-b['random_equity'])<0:ordering_flips+=1
        post_increases=[r for r in post if r['equity']>r['random_equity']]
        summary[label]=dict(notation=RANGES[label],preflop_hands_over50=sum(r['equity']>.5 for r in selected),preflop_ordering_flips_vs_random=ordering_flips,preflop_representatives=[r for r in selected if r['hand'] in ('AA','KK','AKs','AKo','55','22','65s','72o')],flop_states_improving_vs_random=len(post_increases),flop_states=len(post),largest_flop_improvement=max(post,key=lambda r:r['equity']-r['random_equity']),largest_flop_drop=min(post,key=lambda r:r['equity']-r['random_equity']),largest_conditional_rank_mean_shift=max(post,key=lambda r:abs(r['rank_mean']-r['random_rank_mean'])))
    result=dict(samples_per_class_each_tight_range=args.samples,total_new_preflop_samples=args.samples*169*2,summary=summary,prediction_metrics=metrics,public_api_checks=api_checks,elapsed_seconds=time.time()-started)
    (args.output/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
