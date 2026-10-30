import csv,json
from pathlib import Path
root=Path.cwd();d=root/'results/opponent_range_comparison_20261030'
rows=list(csv.DictReader((d/'preflop_comparison.csv').open(encoding='utf-8-sig')))
by={(r['hand'],r['opponent']):r for r in rows}
features=[]
for r in rows:
    if r['opponent']!='tight':continue
    u=by[r['hand'],'ultra_tight']
    features.append(dict(hand=r['hand'],representative=r['representative'],mean_rank_random_exact=r['random_rank_mean_exact'],variance_rank_random_exact=r['random_rank_variance_exact'],equity_random=r['random_equity'],equity_tight=r['equity'],equity_ultra_tight=u['equity'],equity_tight_se=r['equity_se'],equity_ultra_tight_se=u['equity_se']))
with (d/'opponent_strength_features.csv').open('w',newline='',encoding='utf-8-sig') as f:
    w=csv.DictWriter(f,fieldnames=list(features[0]));w.writeheader();w.writerows(features)
source_notes=[dict(year=2013,title='Evaluating State-Space Abstractions in Extensive-Form Games',url='https://johanson.ca/publications/poker/2013-aamas-kmeans-abstraction/2013-aamas-kmeans-abstraction.pdf',relevant='section Opponent Cluster Hand Strength, PDF p.5, eight range-conditioned strength features; distribution-aware abstraction',difference='our three fixed overlapping distributions are not their eight learned clusters or a CFR-BR evaluation'),dict(year=2007,title='Potential-aware Automated Abstraction of Sequential Games, and Holistic Equilibrium Analysis of Texas Hold’em Poker',url='https://cdn.aaai.org/AAAI/2007/AAAI07-008.pdf',relevant='discussion of mean/variance limits and histograms, PDF pp.3-4',difference='our rank moments are ordinal ranks; conditional equity moments are separate; no solver performance comparison'),dict(year=2005,title='Bayes’ Bluff: Opponent Modelling in Poker',url='https://poker.cs.ualberta.ca/publications/UAI05.pdf',relevant='posterior over opponent strategies from observations and responses',difference='our range priors are explicitly assumed, not learned from actions')]
(d/'literature_sources.json').write_text(json.dumps(source_notes,indent=2),encoding='utf-8')
print('Saved 169 range-conditioned feature vectors and primary-source notes')
