"""Check grouped prediction isolation and reproduce saved analysis metrics."""
import csv,json
from pathlib import Path
import numpy as np
from evaluate_preflop_hypotheses import cross_validate

root=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((root/'results/preflop_random_equity/preflop_random_equity.csv').open(encoding='utf-8-sig')))
saved=list(csv.DictReader((root/'results/hypotheses_20261030/heldout_predictions.csv').open(encoding='utf-8-sig')))
x=np.array([[float(r['mean_rank_exact']),float(r['variance_rank_exact'])] for r in rows]);y=np.array([float(r['equity']) for r in rows]);weights=np.ones(len(rows));groups=[r['hand'][:2] for r in rows]
pred=cross_validate(x,y,weights,groups,2,True)
assert len(set(groups))==91
assert np.allclose(pred,[float(r['cv_mean_variance_quadratic']) for r in saved],rtol=0,atol=1e-12)
held=np.array([g=='AK' for g in groups]);modified=y.copy();modified[held]+=.7
other=cross_validate(x,modified,weights,groups,2,True)
assert np.allclose(pred[held],other[held],rtol=0,atol=1e-12)
toy=.2+1e-4*x[:,0]-3e-8*x[:,1]+1e-11*x[:,0]*x[:,1]
toypred=cross_validate(x,toy,weights,groups,2,True)
assert np.max(abs(toypred-toy))<1e-10
metrics=list(csv.DictReader((root/'results/hypotheses_20261030/cross_validation.csv').open(encoding='utf-8-sig')))
for weighting in ('class','combo'):
    w=weights if weighting=='class' else np.array([int(r['combos']) for r in rows])
    for model,field in [('mean_quadratic','cv_mean_quadratic'),('mean_variance_quadratic','cv_mean_variance_quadratic')]:
        p=np.array([float(r[field]) for r in saved]) if weighting=='class' else cross_validate(x,y,w,groups,2,model=='mean_variance_quadratic')
        rmse=100*np.sqrt(np.average((p-y)**2,weights=w))
        m=next(r for r in metrics if r['weighting']==weighting and r['model']==model)
        assert abs(rmse-float(m['rmse_pp']))<1e-10
result=dict(status='passed',rank_pair_groups=91,heldout_labels_do_not_affect_own_predictions=True,synthetic_quadratic_recovery_max_error=float(max(abs(toypred-toy))),saved_predictions_reproduced=True,primary_metrics_reproduced=True)
(root/'results/hypotheses_20261030/analysis_checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
