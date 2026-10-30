"""Exact distribution of opponent-conditioned equity over possible final boards."""
from dataclasses import dataclass, asdict
from itertools import combinations
from math import fsum
from .relative_strength import cards_input, range_pools, card_text
from .cards import create_deck
from .rank_table import rank_seven_cards
from .wildcards import ExpansionLimitError

@dataclass(frozen=True)
class BoardEquityDistribution:
    mean: float
    variance: float
    quantiles: dict
    histogram: list
    boards: int
    deals: int
    conditions: dict

def evaluate_board_distribution(hero, board, opponent, *, dead_cards=(), ranker=None, max_candidates=2000000):
    hero,board,dead=map(cards_input,(hero,board,dead_cards))
    known=hero+board+dead
    if len(hero)!=2 or len(board) not in (3,4,5) or len(set(known))!=len(known):
        raise ValueError('手札2枚と重複のないボード3〜5枚が必要です')
    pool=range_pools([opponent],known)[0]
    deck=[c for c in create_deck() if c not in known]
    missing=5-len(board)
    score=ranker.__getitem__ if ranker is not None else rank_seven_cards
    observations=[]; deals=0
    for runout in combinations(deck,missing):
        final=board+runout
        legal=[(h,w) for h,w in pool if not h.overlaps(runout)]
        if not legal: continue
        deals+=len(legal)
        if deals>max_candidates: raise ExpansionLimitError('全列挙の上限超過。ボードまたはレンジを絞ってください')
        own=score(hero+final)
        weights=fsum(w for _,w in legal)
        share=0.0
        for h,w in legal:
            other=score(h.cards+final)
            share+=w*(1 if own<other else .5 if own==other else 0)
        observations.append((share/weights,weights))
    if not observations: raise ValueError('合法な配布がありません')
    total=fsum(w for _,w in observations)
    mean=fsum(q*w for q,w in observations)/total
    variance=fsum(w*(q-mean)**2 for q,w in observations)/total
    ordered=sorted(observations)
    quantiles={}
    for p in (.1,.5,.9):
        cumulative=0
        for q,w in ordered:
            cumulative+=w
            if cumulative>=p*total:
                quantiles[str(p)]=q;break
    bins=[0.0]*10
    for q,w in observations: bins[min(9,int(q*10))]+=w/total
    return BoardEquityDistribution(mean,variance,quantiles,bins,len(observations),deals,
        dict(hero=card_text(hero),board=card_text(board),dead_cards=card_text(dead),opponent=opponent,method='exact',dictionary_sha256=getattr(ranker,'manifest',{}).get('sha256'),weighting='legal opponent mass per completed board'))
