import hashlib,json,time
from dataclasses import asdict
from poker_evaluator.relative_strength import evaluate_relative_strength
from poker_evaluator.multiway.deal_distribution import MultiwayDealDistribution

def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
t=time.perf_counter()
r=evaluate_relative_strength('5s 5c',[],['random'],samples=10000,seed=733,ranker=lambda c:sum(x.rank for x in c))
relative_seconds=time.perf_counter()-t
t=time.perf_counter()
d=MultiwayDealDistribution(['AA,KK,QQ,AKs,AQs,AJs,KQs']*3,'8s 7h 4d 3c 2s'.split()).sample(10000,seed=733)
multiway_seconds=time.perf_counter()-t
print(json.dumps(dict(relative_seconds=relative_seconds,multiway_seconds=multiway_seconds,relative_sha256=digest(asdict(r)),multiway_sha256=digest([[[(c.rank,c.suit) for c in h.cards] for h in row.hands] for row in d])),indent=2))

