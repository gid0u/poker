"""Check the non-uniform board posterior in tight-range exact data."""
import csv,json
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1];directory=root/'results/opponent_range_comparison_20261030'
def read(name):return list(csv.DictReader((directory/name).open(encoding='utf-8-sig')))
flops=read('flop_comparison.csv');turns=read('turn_comparison.csv');pre=read('preflop_comparison.csv')
assert len(flops)==92 and len(turns)==4324 and len(pre)==338
errors=[];naive=[]
for row in flops:
    children=[r for r in turns if (r['opponent'],r['hero'],r['flop'])==(row['opponent'],row['hero'],row['flop'])]
    weights=np.array([int(r['joint_deals']) for r in children],dtype=float)/(2*int(row['joint_deals']))
    assert abs(weights.sum()-1)<1e-12
    mu=np.array([float(r['rank_mean']) for r in children]);vr=np.array([float(r['rank_variance']) for r in children]);e=np.array([float(r['equity']) for r in children]);vq=np.array([float(r['board_equity_variance']) for r in children])
    parent_mu=float(row['rank_mean']);parent_e=float(row['equity'])
    mean_error=abs(np.dot(weights,mu)-parent_mu);equity_error=abs(np.dot(weights,e)-parent_e)
    variance_error=abs(np.dot(weights,vr+(mu-parent_mu)**2)-float(row['rank_variance']))
    q_variance_error=abs(np.dot(weights,vq+(e-parent_e)**2)-float(row['board_equity_variance']))
    assert mean_error<1e-8 and equity_error<1e-12 and variance_error<1e-6 and q_variance_error<1e-12
    errors.append((float(mean_error),float(equity_error),float(variance_error),float(q_variance_error)))
    naive.append(dict(hero=row['hero'],flop=row['flop'],opponent=row['opponent'],correct_equity=parent_e,incorrect_unweighted_turn_equity=float(np.mean(e)),absolute_bias=float(abs(np.mean(e)-parent_e))))
result=dict(status='passed',flop_parent_states=len(flops),turn_states=len(turns),preflop_estimates=len(pre),max_mean_error=max(r[0] for r in errors),max_equity_error=max(r[1] for r in errors),max_rank_variance_identity_error=max(r[2] for r in errors),max_board_equity_variance_identity_error=max(r[3] for r in errors),largest_naive_unweighted_turn_bias=max(naive,key=lambda r:r['absolute_bias']))
(directory/'posterior_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
