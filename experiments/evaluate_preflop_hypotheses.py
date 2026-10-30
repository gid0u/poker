"""Exploratory hypotheses with rank-pair grouped CV and fresh confirmation."""
import argparse,csv,json
from math import sqrt
from pathlib import Path
from statistics import NormalDist
import numpy as np
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary


def design(x, degree, variance=False):
    columns=[]
    for total in range(degree+1):
        for v_power in range(total+1 if variance else 1):
            columns.append(x[:,0]**(total-v_power)*x[:,1]**v_power)
    return np.column_stack(columns)


def cross_validate(x,y,weights,groups,degree,use_variance):
    predicted=np.empty(len(y))
    for group in dict.fromkeys(groups):
        test=np.array([g==group for g in groups]); train=~test
        center=np.average(x[train],axis=0,weights=weights[train])
        scale=np.sqrt(np.average((x[train]-center)**2,axis=0,weights=weights[train]))
        scale[scale==0]=1
        z=(x-center)/scale
        matrix=design(z,degree,use_variance)
        w=np.sqrt(weights[train])
        coef=np.linalg.lstsq(matrix[train]*w[:,None],y[train]*w,rcond=None)[0]
        predicted[test]=matrix[test]@coef
    return predicted


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dictionary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--confirmation-samples',type=int,default=500000)
    args=parser.parse_args(); args.output.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[1]
    rows=list(csv.DictReader((root/'results/preflop_random_equity/preflop_random_equity.csv').open(encoding='utf-8-sig')))
    config=dict(hypotheses=dict(H1='Adding rank variance reduces out-of-rank-pair CV RMSE at least 10% under both class and combo weighting',H2='Suited-minus-offsuit equity gain is constant across 78 rank pairs',H3='Lower mean final rank always means higher random-opponent equity'),
        primary_models=['mean quadratic (3 coefficients)','mean+variance quadratic (6 coefficients)'],
        sensitivity_models=['mean linear (2)','mean+variance linear (3)','mean quintic (6, equal parameter count)'],
        validation='leave one rank pair out: suited and offsuit are held out together; pairs are separate groups',
        weights=['169 classes equally','physical combos 6/4/12'],
        monte_carlo='existing 1M samples per class are estimated targets; no simultaneous confidence claim for model errors',
        confirmation=dict(selection='largest estimated equity inversion after discovery, then freeze pair before new sampling',samples_each=args.confirmation_samples,seeds=[20261031,20261032],criterion='one-sided direction also excludes zero in two-sided 95% normal difference interval'),
        interpretation='exploratory analysis of 169 fixed classes; cross-validation is not proof of generality to other streets or ranges')
    (args.output/'config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    x=np.array([[float(r['mean_rank_exact']),float(r['variance_rank_exact'])] for r in rows]); y=np.array([float(r['equity']) for r in rows]); se=np.array([float(r['equity_standard_error']) for r in rows])
    groups=[r['hand'][:2] for r in rows]
    specs=[('mean_linear',1,False),('mean_variance_linear',1,True),('mean_quadratic',2,False),('mean_variance_quadratic',2,True),('mean_quintic',5,False)]
    metrics=[]; predictions={}
    for weighting in ('class','combo'):
        weights=np.ones(len(rows)) if weighting=='class' else np.array([int(r['combos']) for r in rows],dtype=float)
        for name,degree,use_var in specs:
            pred=cross_validate(x,y,weights,groups,degree,use_var)
            error=pred-y
            metrics.append(dict(weighting=weighting,model=name,rmse_pp=100*sqrt(np.average(error**2,weights=weights)),mae_pp=100*np.average(abs(error),weights=weights),max_absolute_error_pp=100*max(abs(error))))
            predictions[weighting+'_'+name]=pred
    with (args.output/'cross_validation.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
    residual=[]
    p=predictions['class_mean_variance_quadratic']
    for i,r in enumerate(rows):
        residual.append(dict(hand=r['hand'],kind=r['kind'],equity=y[i],equity_se=se[i],mean_rank=x[i,0],variance_rank=x[i,1],cv_mean_quadratic=predictions['class_mean_quadratic'][i],cv_mean_variance_quadratic=p[i],residual_pp=100*(y[i]-p[i])))
    with (args.output/'heldout_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(residual[0]));w.writeheader();w.writerows(residual)
    by={r['hand']:i for i,r in enumerate(rows)}; pairs=[]
    critical=NormalDist().inv_cdf(1-.05/(2*78))
    for i,r in enumerate(rows):
        if r['kind']=='suited':
            j=by[r['hand'][:-1]+'o']; gap=y[i]-y[j]; gap_se=sqrt(se[i]**2+se[j]**2)
            pairs.append(dict(suited=r['hand'],gap=gap,se=gap_se,simultaneous95_low=gap-critical*gap_se,simultaneous95_high=gap+critical*gap_se))
    gaps=np.array([r['gap'] for r in pairs]); gap_se=np.array([r['se'] for r in pairs]); inv=1/gap_se**2
    constant=np.average(gaps,weights=inv); q=float(np.sum(((gaps-constant)/gap_se)**2))
    inversions=[]
    comparisons=len(rows)*(len(rows)-1)//2
    zcrit=NormalDist().inv_cdf(1-.05/(2*comparisons))
    for i in range(len(rows)):
        for j in range(i+1,len(rows)):
            stronger,weaker=(i,j) if x[i,0]<x[j,0] else (j,i)
            gap=y[weaker]-y[stronger]
            if gap>0:
                combined=sqrt(se[stronger]**2+se[weaker]**2)
                inversions.append(dict(better_mean_hand=rows[stronger]['hand'],worse_mean_hand=rows[weaker]['hand'],mean_rank_difference=x[weaker,0]-x[stronger,0],reverse_equity_gap=gap,se=combined,bonferroni95_low=gap-zcrit*combined))
    selected=max(inversions,key=lambda r:r['reverse_equity_gap'])
    (args.output/'confirmation_selection.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
    with SevenCardRankDictionary(args.dictionary) as table:
        confirm=[]
        for label,seed in zip((selected['better_mean_hand'],selected['worse_mean_hand']),[20261031,20261032]):
            r=rows[by[label]]
            value=table.relative_strength(r['representative'],[],['random'],samples=args.confirmation_samples,seed=seed)
            confirm.append(dict(hand=label,representative=r['representative'],samples=value.outcomes,equity=value.equity,se=value.equity_standard_error,seed=seed))
            print('fresh confirmation: '+str(confirm[-1]),flush=True)
    gap=confirm[1]['equity']-confirm[0]['equity']; combined=sqrt(sum(r['se']**2 for r in confirm))
    m={(r['weighting'],r['model']):r for r in metrics}
    improvements={weight:1-m[weight,'mean_variance_quadratic']['rmse_pp']/m[weight,'mean_quadratic']['rmse_pp'] for weight in ('class','combo')}
    result=dict(H1=dict(primary_rmse_improvement=improvements,supported_in_primary_test=all(v>=.1 for v in improvements.values()),metrics=metrics,largest_residuals=sorted(residual,key=lambda r:abs(r['residual_pp']),reverse=True)[:8]),
        H2=dict(constant_gain_estimate=constant,heterogeneity_Q=q,degrees_of_freedom=77,Q_over_df=q/77,normal_approximation_assumed=True,
            min_pair=min(pairs,key=lambda r:r['gap']),max_pair=max(pairs,key=lambda r:r['gap']),all_78_simultaneous95_gain_lower_bounds_positive=all(r['simultaneous95_low']>0 for r in pairs),bonferroni_z=critical),
        H3=dict(pairwise_comparisons=comparisons,estimated_inversions=len(inversions),simultaneous95_clear_inversions=sum(r['bonferroni95_low']>0 for r in inversions),discovery=selected,fresh_confirmation=confirm,fresh_gap=gap,fresh_gap_ci95=[gap-1.96*combined,gap+1.96*combined],direction_confirmed=gap-1.96*combined>0))
    (args.output/'results.json').write_text(json.dumps(result,indent=2,default=lambda value:value.item()),encoding='utf-8')
    print(json.dumps(result,indent=2,default=lambda value:value.item()),flush=True)

if __name__=='__main__':main()

