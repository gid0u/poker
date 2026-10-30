"""Exact postflop hypotheses over a fixed panel of real-card states vs random HU."""
import argparse,csv,json,time
from itertools import combinations
from math import comb,isclose
from pathlib import Path
import numpy as np
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary,card_id
from preflop_random_equity import lookup

BOARDS=['Ks 8h 7d','Ts 9s 2c','Qs Js 8s','9c 9h 2d','7s 6h 5d','Ac Kd 4h']
HEROES=['As Ah','Kc Kh','Qc Qh','As Ks','Qs Js','6s 5s','5c 5h','7c 2h']

def text(ids):return ' '.join('23456789TJQKA'[int(c)//4]+'schd'[int(c)%4] for c in ids)
def moments(values,denominator=1):
    n=len(values);s=sum(int(v) for v in values);ss=sum(int(v)**2 for v in values)
    return s/(n*denominator),(ss*n-s*s)/(n*n*denominator*denominator)
def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dictionary',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);started=time.time()
    config=dict(hypotheses=dict(H1='Rank variance never increases on a particular flop-to-turn branch',H2='On the river, zero rank variance implies equity is zero or one',H3='Larger rank variance always means larger variance of board-conditional equity',H4='The equity ordering of two hands is independent of opponent range'),boards=BOARDS,hero_real_cards=HEROES,
        selection='fixed 6 textures x 8 hero representatives, discard card collisions',method='exact uniform remaining board pairs and all 990 legal opponent hands on each final board',
        measure='one uniform random opponent, shared board, showdown; q(B)=equity conditional on the completed board',
        checks='conditional total variance identities; independent public API exact turn and river checks; public API sampling on flops',
        limits='finite designed state panel; not all possible flops or hole cards; no betting decisions')
    (args.output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    choose=np.array([[comb(c,k) for c in range(52)] for k in range(1,8)],dtype=np.int64)
    values=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r')
    opponent_indices=np.array(list(combinations(range(45),2)),dtype=np.int16)
    flops=[];turns=[];rivers=[];all_law_errors=[];all_q_errors=[];max_spread=None;skipped=[]
    for board_text in BOARDS:
        board=[card_id(c) for c in board_text.split()]
        for hero_text in HEROES:
            hero=[card_id(c) for c in hero_text.split()]
            if len(set(hero+board))!=5:
                skipped.append(dict(hero=hero_text,flop=board_text));continue
            available=[c for c in range(52) if c not in hero+board]
            by_turn={c:[] for c in available};ranks=[];shares=[];tie_count=0;by_rank={}
            for a,b in combinations(available,2):
                final=board+[a,b]
                ours=np.array([hero+final],dtype=np.uint8)
                rank=int(lookup(ours,values,choose)[0])
                deck=np.array([c for c in available if c not in (a,b)],dtype=np.uint8)
                villains=np.empty((990,7),dtype=np.uint8);villains[:,:2]=deck[opponent_indices];villains[:,2:]=final
                opposing=lookup(villains,values,choose)
                wins=int((rank<opposing).sum());ties=int((rank==opposing).sum());k=2*wins+ties
                ranks.append(rank);shares.append(k);tie_count+=ties
                by_turn[a].append((rank,k));by_turn[b].append((rank,k))
                river=dict(hero=hero_text,flop=board_text,board=text(final),rank=rank,rank_variance=0,equity=k/1980,win_probability=wins/990,tie_probability=ties/990,opponent_combos=990)
                rivers.append(river)
                low,high=by_rank.get(rank,(river,river))
                if river['equity']<low['equity']:low=river
                if river['equity']>high['equity']:high=river
                by_rank[rank]=(low,high)
            mu,vr=moments(ranks);e,vq=moments(shares,1980)
            assert len(ranks)==1081
            row=dict(hero=hero_text,flop=board_text,rank_mean=mu,rank_variance=vr,equity=e,board_equity_variance=vq,expected_squared_board_equity=vq+e*e,tie_probability=tie_count/(1081*990),completed_boards=1081,joint_deals=1081*990)
            local=[]
            for c,outcomes in by_turn.items():
                assert len(outcomes)==46
                mr,vt=moments([r for r,k in outcomes]);qe,qv=moments([k for r,k in outcomes],1980)
                tr=dict(hero=hero_text,flop=board_text,turn_card=text([c]),board=text(board+[c]),rank_mean=mr,rank_variance=vt,equity=qe,board_equity_variance=qv,expected_squared_board_equity=qv+qe*qe,
                    rank_variance_change_from_flop=vt-vr,completed_boards=46,joint_deals=46*990)
                local.append(tr);turns.append(tr)
            mean_mu=np.mean([r['rank_mean'] for r in local]);mean_e=np.mean([r['equity'] for r in local])
            err=abs(vr-(np.mean([r['rank_variance'] for r in local])+np.var([r['rank_mean'] for r in local])))
            qerr=abs(vq-(np.mean([r['board_equity_variance'] for r in local])+np.var([r['equity'] for r in local])))
            assert abs(mean_mu-mu)<1e-8 and abs(mean_e-e)<1e-12 and err<1e-7 and qerr<1e-12
            all_law_errors.append(float(err));all_q_errors.append(float(qerr))
            row['turn_branches_with_increased_rank_variance']=sum(r['rank_variance']>vr+1e-8 for r in local)
            row['expected_turn_rank_variance']=float(np.mean([r['rank_variance'] for r in local]))
            row['variance_of_turn_rank_means']=float(np.var([r['rank_mean'] for r in local]))
            row['rank_uncertainty_resolved_fraction']=row['variance_of_turn_rank_means']/vr if vr else 0
            flops.append(row)
            for low,high in by_rank.values():
                spread=high['equity']-low['equity']
                if max_spread is None or spread>max_spread['equity_gap']:
                    max_spread=dict(equity_gap=spread,low_equity_state=low,high_equity_state=high)
            print(f'{len(flops)} states: {hero_text} / {board_text} ({time.time()-started:.1f}s)',flush=True)
    increases=[r for r in turns if r['rank_variance_change_from_flop']>1e-8]
    inversions=[]
    for a,b in combinations(flops,2):
        if (a['rank_variance']-b['rank_variance'])*(a['board_equity_variance']-b['board_equity_variance'])<0:
            high,low=(a,b) if a['rank_variance']>b['rank_variance'] else (b,a)
            inversions.append(dict(higher_rank_variance=high,lower_rank_variance=low,equity_variance_reversal=low['board_equity_variance']-high['board_equity_variance']))
    with SevenCardRankDictionary(args.dictionary) as table:
        range_states=[]
        for hero in ('As Ah','Qs Js'):
            random=next(r for r in flops if r['hero']==hero and r['flop']=='Ts 9s 2c')
            strong=table.relative_strength(hero,'Ts 9s 2c',['TT,99'],mode='exact',max_candidates=100000)
            range_states.append(dict(hero=hero,flop='Ts 9s 2c',random_equity=random['equity'],set_range_equity=strong.equity,set_range_outcomes=strong.outcomes))
        range_reversal=(range_states[0]['random_equity']-range_states[1]['random_equity'])*(range_states[0]['set_range_equity']-range_states[1]['set_range_equity'])<0
        checks=[]
        for row in (turns[0],turns[-1],max(increases,key=lambda r:r['rank_variance_change_from_flop'])):
            actual=table.relative_strength(row['hero'],row['board'],['random'],mode='exact')
            assert abs(actual.equity-row['equity'])<1e-10 and isclose(actual.variance_rank,row['rank_variance'],rel_tol=1e-11,abs_tol=1e-6)
            checks.append(dict(street='turn',hero=row['hero'],board=row['board'],exact_outcomes=actual.outcomes,variance_absolute_error=abs(actual.variance_rank-row['rank_variance']),equity_absolute_error=abs(actual.equity-row['equity'])))
        for row in (max_spread['low_equity_state'],max_spread['high_equity_state']):
            actual=table.relative_strength(row['hero'],row['board'],['random'],mode='exact')
            assert actual.mean_rank==row['rank'] and abs(actual.equity-row['equity'])<1e-10
            checks.append(dict(street='river',hero=row['hero'],board=row['board'],exact_outcomes=actual.outcomes))
        for i,row in enumerate((flops[0],flops[-1])):
            sampled=table.relative_strength(row['hero'],row['flop'],['random'],samples=20000,seed=20261030+i)
            z=abs(sampled.equity-row['equity'])/sampled.equity_standard_error
            assert z<5
            checks.append(dict(street='flop',hero=row['hero'],board=row['flop'],samples=sampled.outcomes,abs_z=z))
    result=dict(method='exact enumeration; except explicitly labeled sampling checks',flop_states=len(flops),turn_states=len(turns),river_states=len(rivers),skipped_collisions=skipped,
        total_flop_joint_deals=sum(r['joint_deals'] for r in flops),
        H1=dict(increasing_turn_branches=len(increases),all_turn_branches=len(turns),largest_increase=max(increases,key=lambda r:r['rank_variance_change_from_flop']) if increases else None,
            all_flop_expected_turn_variance_not_larger=all(r['expected_turn_rank_variance']<=r['rank_variance']+1e-7 for r in flops),max_rank_total_variance_error=max(all_law_errors),max_equity_total_variance_error=max(all_q_errors)),
        H2=dict(river_states_with_strictly_intermediate_equity=sum(0<r['equity']<1 for r in rivers),river_states_total=len(rivers),largest_same_hero_flop_rank_equity_gap=max_spread),
        H3=dict(flop_pair_comparisons=comb(len(flops),2),rank_variance_vs_equity_variance_inversions=len(inversions),largest_inversion=max(inversions,key=lambda r:r['equity_variance_reversal']) if inversions else None),
        H4=dict(states=range_states,ordering_reversed=range_reversal),public_api_checks=checks,elapsed_seconds=time.time()-started)
    write_csv(args.output/'flop_states.csv',flops);write_csv(args.output/'turn_states.csv',turns);write_csv(args.output/'river_states.csv',rivers)
    (args.output/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
