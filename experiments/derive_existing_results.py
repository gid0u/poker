"""Derive identities and exact finite-dataset properties from existing artifacts."""
import argparse,csv,json
from fractions import Fraction
from math import sqrt
from pathlib import Path
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dictionary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    rows=list(csv.DictReader((root/'results/preflop_rank_scatter/preflop_rank_scatter.csv').open(encoding='utf-8-sig')))
    eq=list(csv.DictReader((root/'results/preflop_random_equity/preflop_random_equity.csv').open(encoding='utf-8-sig')))
    by={r['hand']:r for r in rows}; equities={r['hand']:r for r in eq}
    def mean(r): return Fraction(int(r['rank_sum']),int(r['boards']))
    def variance(r): return Fraction(int(r['rank_squared_sum']),int(r['boards']))-mean(r)**2
    weights={r['hand']:Fraction(int(r['combos']),1326) for r in rows}
    mu=sum(weights[r['hand']]*mean(r) for r in rows)
    within=sum(weights[r['hand']]*variance(r) for r in rows)
    between=sum(weights[r['hand']]*(mean(r)-mu)**2 for r in rows)
    total=within+between
    best_mean=min(rows,key=mean); best_var=min(rows,key=variance)
    assert best_mean['hand']==best_var['hand']=='AA'
    assert all(mean(r)>mean(by['AA']) and variance(r)>variance(by['AA']) for r in rows if r['hand']!='AA')
    dominated=[r['hand'] for r in rows if mean(by['AA'])<=mean(r) and variance(by['AA'])<=variance(r)]
    assert len(dominated)==169
    paired=[]
    for r in rows:
        if r['kind']=='suited':
            off=by[r['hand'][:-1]+'o']; e1,e2=equities[r['hand']],equities[off['hand']]
            gain=float(mean(off)-mean(r)); delta=float(variance(r)-variance(off))
            assert gain>0 and delta>0
            paired.append(dict(suited=r['hand'],offsuit=off['hand'],mean_rank_improvement_exact=gain,
                variance_increase_exact=delta,equity_improvement_estimate=float(e1['equity'])-float(e2['equity']),
                equity_difference_se=sqrt(float(e1['equity_standard_error'])**2+float(e2['equity_standard_error'])**2)))
    with SevenCardRankDictionary(args.dictionary) as table:
        base=table.all_hands_statistics
        assert mu==Fraction(base['rank_sum'],base['hand_count'])
        assert total==Fraction(base['rank_squared_sum'],base['hand_count'])-mu*mu
        examples=[]
        for board in ('Ks 8h 7d 3c 2s','Kc 8c 7c 3h 2s'):
            r=table.relative_strength('As Ah',board,['random'],mode='exact')
            examples.append(dict(hero='As Ah',board=board,mean_rank=r.mean_rank,variance_rank=r.variance_rank,
                equity=r.equity,win_probability=r.win_probability,tie_probability=r.tie_probability,opponent_combos=r.outcomes))
        assert examples[0]['mean_rank']==examples[1]['mean_rank']
        assert examples[0]['variance_rank']==examples[1]['variance_rank']==0
        assert examples[0]['equity']!=examples[1]['equity']
    r=equities['55']; e=float(r['equity']); t=float(r['tie_probability']); n=int(r['samples'])
    payoff_variance=e*(1-e)-t/4
    assert abs(sqrt(payoff_variance/(n-1))-float(r['equity_standard_error']))<1e-12
    summary=dict(exact_variance_decomposition=dict(mean_rank=float(mu),total_rank_variance=float(total),
        expected_conditional_rank_variance=float(within),variance_of_conditional_means=float(between),
        within_fraction=float(within/total),between_fraction=float(between/total),exact_fraction_identity=str(total)),
        finite_dataset_properties=dict(classes=169,min_mean_hand=best_mean['hand'],min_variance_hand=best_var['hand'],
            hands_weakly_dominated_by_AA_in_minimizing_mean_and_variance=len(dominated),suited_offsuit_pairs=78,
            all_suited_mean_rank_better=True,all_suited_rank_variance_larger=True,
            min_suited_mean_improvement=min(paired,key=lambda r:r['mean_rank_improvement_exact']),
            max_suited_mean_improvement=max(paired,key=lambda r:r['mean_rank_improvement_exact']),
            min_suited_equity_gain_estimate=min(paired,key=lambda r:r['equity_improvement_estimate']),
            max_suited_equity_gain_estimate=max(paired,key=lambda r:r['equity_improvement_estimate'])),
        exact_counterexample_same_mean_variance_different_random_equity=examples,
        share_variance_55_estimate=dict(equity=e,tie_probability=t,showdown_share_variance=payoff_variance,
            board_conditional_equity_variance_lower_bound=0,board_conditional_equity_variance_upper_bound=payoff_variance,
            note='share variance reconstructed from estimated equity and ties; not the variance of board-conditional equity'))
    (args.output/'derivations.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    with (args.output/'suited_offsuit_differences.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(paired[0])); w.writeheader(); w.writerows(paired)
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__': main()
