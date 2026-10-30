"""Count legal tight-range opponent allocations exactly using matching polynomials."""
import json
from fractions import Fraction
from functools import lru_cache
from math import comb
from pathlib import Path

from poker_evaluator.range_parser import parse_range
from poker_evaluator.seven_card_dictionary import card_id

OUT = Path(__file__).resolve().parents[1] / 'results/rigorous_99_tt_20261030'
POOL = [tuple(sorted(card_id(c) for c in hand.cards)) for hand in parse_range('99+,AQs+,AKo')]

def count(edges, k):
    """Count unordered matchings of k edges; decompose the graph into components."""
    vertices = set(x for e in edges for x in e)
    adj = {v: set() for v in vertices}
    for a,b in edges:
        adj[a].add(b); adj[b].add(a)
    components = []
    while vertices:
        todo = [next(iter(vertices))]; component = set()
        while todo:
            v = todo.pop()
            if v in component: continue
            component.add(v); todo.extend(adj[v] - component)
        vertices -= component; components.append(sorted(component))
    result = [1]
    for component in components:
        indexes = {v:i for i,v in enumerate(component)}
        masks = [sum(1 << indexes[u] for u in adj[v]) for v in component]
        @lru_cache(None)
        def poly(mask):
            if not mask: return (1,)
            bit = mask & -mask; i = bit.bit_length()-1; rest = mask ^ bit
            out = list(poly(rest)); neighbors = masks[i] & rest
            while neighbors:
                b = neighbors & -neighbors; neighbors ^= b
                part = poly(rest ^ b)
                if len(out) < len(part)+1: out.extend([0]*(len(part)+1-len(out)))
                for j,x in enumerate(part): out[j+1] += x
            return tuple(out)
        component_poly = poly((1 << len(component))-1)
        product = [0] * (len(result)+len(component_poly)-1)
        for i,x in enumerate(result):
            for j,y in enumerate(component_poly): product[i+j] += x*y
        result = product[:k+1]
    return result[k] if k < len(result) else 0

def calculate(hero):
    hero = {card_id(c) for c in hero.split()}
    edges = [e for e in POOL if not hero.intersection(e)]
    total = count(edges, 8)
    expected = {}; probabilities = {}
    for rank,label in [(7,'99'),(8,'TT'),(9,'JJ'),(10,'QQ'),(11,'KK'),(12,'AA')]:
        group = [e for e in edges if all(c//4 == rank for c in e)]
        numerator = sum(count([e for e in edges if not set(e).intersection(edge)], 7) for edge in group)
        expected[label] = Fraction(numerator,total)
        probabilities[label] = Fraction(total-count([e for e in edges if e not in group],8),total)
    # Independent ordered two-player enumeration verifies the matching counter.
    brute = sum(not set(a).intersection(b) for a in edges for b in edges)
    assert brute == 2*count(edges,2)
    return total, expected, probabilities

def show(f): return {'numerator': f.numerator, 'denominator': f.denominator, 'value': float(f)}
def main():
    total,a,prob = calculate('9s 9c'); total_t,b,_ = calculate('Ts Tc')
    assert total == total_t and a['99'] == b['TT'] and a['TT'] == b['99']
    deck9 = 2 - 2*a['99']; deckt = 4 - 2*a['TT']
    nboards = comb(34,5)
    result = {'unordered_opponent_matchings':total,
              'labelled_opponent_deals':total*40320,
              'expected_opponent_pair_counts_hero99':{k:show(v) for k,v in a.items()},
              'probability_any_opponent_pair_hero99':{k:show(v) for k,v in prob.items()},
              'expected_board_9_count_hero99':show(deck9*Fraction(5,34)),
              'expected_board_T_count_hero99':show(deckt*Fraction(5,34)),
              'board_high_card_count_probabilities':{str(i):show(Fraction(comb(6,i)*comb(28,5-i),nboards)) for i in range(6)},
              'explanation':'Each legal matching has 8! labelled seat assignments. All 16 opposing cards are 9 or higher; 6 of the 34 remaining cards are 9 or higher. Uniform five-card board.',
              'check':'Rank-swap counts match; exact two-opponent count verified against ordered brute force.'}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'exact_matching.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__ == '__main__': main()
