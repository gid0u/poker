"""Independent consistency checks against the existing full dictionary and datasets."""
import argparse,csv,json,platform,time
from datetime import datetime,timezone
from itertools import permutations,product
from math import comb,fsum,sqrt
from pathlib import Path
from random import Random
import numpy as np
from poker_evaluator.cards import Card,parse_card
from poker_evaluator.evaluate7 import evaluate7
from poker_evaluator.range_parser import HandCombo
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary,index_cards,hand_index,HAND_COUNT
from poker_evaluator.relative_strength import evaluate_relative_strength
from poker_evaluator.multiway import RiverGame,MultiwayDealDistribution,WeightedRange


def hand(text): return HandCombo(*(parse_card(c) for c in text.split()))
def remap(text,suits):
    return ' '.join(t[0]+'schd'[suits['schd'.index(t[1])]] for t in text.split())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--dictionary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    started=time.time(); rng=Random(20261030)
    report={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'seed':20261030,'python':platform.python_version(),'checks':{}}
    def passed(name,**details):
        report['checks'][name]={'status':'passed',**details}
        print(name+': passed',flush=True)
    with SevenCardRankDictionary(args.dictionary,verify_checksum=True) as table:
        report['dictionary_sha256']=table.manifest['sha256']
        data=np.memmap(args.dictionary/'seven_card_ranks.u16',dtype='<u2',mode='r')
        counts=np.zeros(7463,dtype=np.int64)
        for start in range(0,HAND_COUNT,2_000_000):
            block=data[start:start+2_000_000]
            assert np.all((block>=1)&(block<=7462))
            counts+=np.bincount(block,minlength=7463)
        baseline=table.all_hands_statistics
        assert {str(i):int(n) for i,n in enumerate(counts) if n}==baseline['rank_counts']
        assert sum(int(n) for n in counts)==HAND_COUNT
        assert sum(i*int(n) for i,n in enumerate(counts))==baseline['rank_sum']
        assert sum(i*i*int(n) for i,n in enumerate(counts))==baseline['rank_squared_sum']
        passed('complete_dictionary_integrity',entries=HAND_COUNT,checksum_verified=True,rank_histogram_matches=True)
        for _ in range(1000):
            cards=tuple(Card(i//4+2,i%4) for i in rng.sample(range(52),7))
            assert table.value(cards)==evaluate7(list(cards))
            assert hand_index(index_cards(hand_index(cards)))==hand_index(cards)
            shuffled=list(cards); rng.shuffle(shuffled)
            assert table[cards]==table[shuffled]
        passed('independent_evaluator_and_index',random_hands=1000,reference='max over 21 five-card evaluations')
        hero='As Qs'; board='Kh 8c 7d 3h'; ranges=['KK,JJ,TT']
        reference=table.relative_strength(hero,board,ranges,mode='exact')
        for suit_map in permutations(range(4)):
            mapped=table.relative_strength(remap(hero,suit_map),remap(board,suit_map),ranges,mode='exact')
            for field in ('mean_rank','variance_rank','win_probability','tie_probability','equity'):
                assert abs(getattr(reference,field)-getattr(mapped,field))<1e-7
        order=table.relative_strength('Qs As','3h 7d 8c Kh',ranges,mode='exact')
        assert abs(order.equity-reference.equity)<1e-12
        passed('relative_suit_and_order_invariance',suit_permutations=24,exact_outcomes=reference.outcomes)
        pairs=[('As Ah','Kc Kd'),('Qs Js','Tc Th'),('2s 2c','Ad Qd'),('9s Ts','Ac Kc')]
        for a,b in pairs:
            x=table.relative_strength(a,board,[[hand(b)]],mode='exact')
            y=table.relative_strength(b,board,[[hand(a)]],mode='exact')
            assert abs(x.equity+y.equity-1)<1e-12
            assert abs(x.win_probability-y.loss_probability)<1e-12
            assert x.tie_probability==y.tie_probability
        passed('heads_up_swap_complement',fixed_hand_pairs=len(pairs))
        exact=table.relative_strength('As Ah',board,['KK,QQ'],mode='exact')
        zscores=[]
        for seed in range(10):
            sample=table.relative_strength('As Ah',board,['KK,QQ'],samples=10000,seed=seed)
            z=abs(sample.equity-exact.equity)/sample.equity_standard_error
            assert z<5
            zscores.append(z)
        passed('sampling_against_exact',seeds=10,samples_each=10000,exact_equity=exact.equity,max_abs_z=max(zscores),acceptance='5 standard errors; not a 95% coverage proof')
        explicit=table.relative_strength('As Ah',board,['KK,QQ'],mode='exact')
        wild=table.relative_wildcards('As Ah Kh 8c 7d 3h X1',['KK,QQ'])
        assert abs(explicit.mean_rank-wild.mean_rank)<1e-8
        assert abs(explicit.variance_rank-wild.variance_rank)<1e-7
        assert abs(explicit.equity-wild.equity)<1e-12
        passed('wildcard_explicit_equivalence',outcomes=wild.outcomes)
        terminal=[('check',)]+[('bet',)+x for x in product(('fold','call'),repeat=2)]
        for _ in range(200):
            c=[Card(i//4+2,i%4) for i in rng.sample(range(52),11)]
            pot=rng.uniform(0,1000); bet=rng.uniform(1,100)
            game=RiverGame(tuple(c[:5]),pot=pot,bet=bet,stacks=(bet,bet,bet))
            hands=tuple(HandCombo(c[5+2*i],c[6+2*i]) for i in range(3))
            for history in terminal:
                payoff=game.payoff(hands,history)
                assert abs(sum(payoff)-pot)<1e-9
                assert all(-bet-1e-9<=v<=pot+2*bet+1e-9 for v in payoff)
                if history[0]=='bet':
                    for i in (1,2):
                        if history[i]=='fold': assert payoff[i]==0
        passed('multiway_payoff_conservation',random_deals=200,terminal_histories_each=5,payoffs_checked=1000)
        dist=MultiwayDealDistribution([WeightedRange(((hand('As Ah'),2),(hand('Qc Qh'),1))),
            [hand('As Ac'),hand('Jc Jh')],[hand('Tc Th')]],'Ks 8h 7d 3c 2s'.split())
        exact_deals=dist.exact(); draws=dist.sample(20000,seed=42)
        assert abs(sum(d.probability for d in exact_deals)-1)<1e-12
        for deal in exact_deals:
            p=deal.probability; observed=sum(d.hands==deal.hands for d in draws)/len(draws)
            assert abs(observed-p)<5*sqrt(p*(1-p)/len(draws))
        passed('weighted_joint_deal_sampling',exact_legal_deals=len(exact_deals),samples=20000,acceptance='5 binomial standard errors')
        root=Path(__file__).resolve().parents[1]
        moments=list(csv.DictReader((root/'results/preflop_rank_scatter/preflop_rank_scatter.csv').open(encoding='utf-8-sig')))
        equity=list(csv.DictReader((root/'results/preflop_random_equity/preflop_random_equity.csv').open(encoding='utf-8-sig')))
        assert len(moments)==len(equity)==169
        assert len({r['hand'] for r in equity})==169
        assert sum(int(r['combos']) for r in moments)==1326
        mu=fsum(float(r['mean_rank'])*int(r['combos']) for r in moments)/1326
        second=fsum((float(r['variance_rank'])+float(r['mean_rank'])**2)*int(r['combos']) for r in moments)/1326
        assert abs(mu-baseline['mean_rank'])<1e-8
        assert abs(second-mu*mu-baseline['variance_rank'])<1e-6
        e=fsum(float(r['equity'])*int(r['combos'])/1326 for r in equity)
        se=sqrt(fsum((float(r['equity_standard_error'])*int(r['combos'])/1326)**2 for r in equity))
        assert abs(e-.5)<5*se
        for r in equity:
            n=int(r['samples']); w=int(r['wins']); t=int(r['ties']); l=int(r['losses'])
            assert w+t+l==n
            assert abs((w+t/2)/n-float(r['equity']))<1e-14
            assert float(r['equity_ci95_low'])<=float(r['equity'])<=float(r['equity_ci95_high'])
        fresh=[]
        for label in ('AA','55','72o'):
            r=next(r for r in equity if r['hand']==label)
            s=table.relative_strength(r['representative'],[],['random'],samples=100000,seed=20261030)
            combined=sqrt(s.equity_standard_error**2+float(r['equity_standard_error'])**2)
            z=abs(s.equity-float(r['equity']))/combined
            assert z<5
            fresh.append({'hand':label,'new_equity':s.equity,'saved_equity':float(r['equity']),'abs_z':z})
        passed('saved_preflop_dataset_consistency',classes=169,weighted_mean=mu,weighted_variance=second-mu*mu,weighted_equity=e,weighted_equity_z=abs(e-.5)/se,fresh_sampling=fresh)
    report['elapsed_seconds']=time.time()-started
    report['status']='passed'
    (args.output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)

if __name__=='__main__': main()

