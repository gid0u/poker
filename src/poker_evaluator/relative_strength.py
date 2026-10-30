"""Conditional showdown rank dispersion and equity under one shared deal law."""
from collections import Counter
from dataclasses import dataclass
from itertools import combinations, accumulate
from math import comb, fsum, sqrt
from random import Random

from .cards import Card, create_deck, parse_card
from .range_parser import HandCombo
from .multiway.deal_distribution import WeightedRange
from .rank_table import rank_seven_cards
from .seven_card_dictionary import SevenCardRankDictionary, card_id
from .wildcards import WildcardPattern, ExpansionLimitError


def cards_input(cards):
    values = cards.split() if isinstance(cards, str) else tuple(cards)
    result = tuple(parse_card(c) if isinstance(c, str) else c for c in values)
    if any(not isinstance(c, Card) for c in result) or len(set(result)) != len(result):
        raise ValueError("Cards must be distinct real cards")
    return result


def card_text(cards):
    return ["23456789TJQKA"[c.rank-2]+"schd"[c.suit] for c in cards]


def range_pools(ranges, blocked):
    if not 1 <= len(ranges) <= 8:
        raise ValueError("Specify one to eight opponent ranges")
    pools = []
    for value in ranges:
        if isinstance(value, str) and value.lower().strip() == "random":
            value = tuple(HandCombo(*c) for c in combinations(create_deck(), 2))
        entries = tuple((combo, weight) for combo, weight in WeightedRange.from_range(value).entries
                        if not combo.overlaps(blocked))
        pools.append(WeightedRange(entries).entries)
    return tuple(pools)


@dataclass(frozen=True)
class RelativeStrength:
    mean_rank: float
    variance_rank: float
    standard_deviation_rank: float
    win_probability: float
    tie_probability: float
    loss_probability: float
    equity: float
    equity_standard_error: float
    equity_ci95: tuple[float, float]
    outcomes: int
    method: str
    conditions: dict


def aggregate(cases, ranker, mode, conditions):
    score = ranker.__getitem__ if isinstance(ranker, SevenCardRankDictionary) else ranker or rank_seven_cards
    ranks = Counter()
    wins = ties = losses = share_sum = share_square = total = 0.0
    count = 0
    for hero, board, opponents, mass in cases:
        values = [score(tuple(hero)+tuple(board))] + [score(tuple(h)+tuple(board)) for h in opponents]
        best = min(values)
        winners = values.count(best)
        share = (1/winners) if values[0] == best else 0.0
        if share == 1:
            wins += mass
        elif share > 0:
            ties += mass
        else:
            losses += mass
        ranks[values[0]] += mass
        total += mass
        share_sum += mass*share
        share_square += mass*share*share
        count += 1
    if count == 0 or total <= 0:
        raise ValueError("No legal positive-mass joint deal")
    mean = fsum(r*w for r, w in ranks.items())/total
    variance = fsum(w*(r-mean)**2 for r, w in ranks.items())/total
    equity = share_sum/total
    se = sqrt(max(0.0, share_square/total-equity**2)/(count-1)) if mode == "sampling" else 0.0
    return RelativeStrength(mean, variance, sqrt(variance), wins/total, ties/total, losses/total,
                            equity, se, (max(0., equity-1.96*se), min(1., equity+1.96*se)),
                            count, mode, conditions)


def describe_pools(pools):
    return [[dict(cards=["23456789TJQKA"[c.rank-2]+"schd"[c.suit] for c in h.cards], weight=w)
             for h, w in pool] for pool in pools]


def evaluate_relative_strength(hero, board, opponent_ranges, *, dead_cards=(), mode="sampling",
                               samples=10000, seed=42, max_candidates=1000000,
                               max_attempts=None, ranker=None):
    """Known hero and observed board; future board cards are unknown (uniform).

    Opponent combo weights are independent priors conditioned JOINTLY on legality.
    Sample full independent opponent draws and reject collisions, then draw runout.
    No strategic action model, rake or side pots; all opponents reach showdown.
    """
    hero, board, dead = cards_input(hero), cards_input(board), cards_input(dead_cards)
    if len(hero) != 2 or len(board) not in (0, 3, 4, 5):
        raise ValueError("Hero needs two cards; board needs 0, 3, 4 or 5")
    blocked = hero+board+dead
    if len(set(blocked)) != len(blocked):
        raise ValueError("Hero, board and dead cards overlap")
    pools = range_pools(opponent_ranges, blocked)
    missing = 5-len(board)
    remaining_count = 52-len(blocked)-2*len(pools)
    if remaining_count < missing:
        raise ValueError("Insufficient cards")
    if mode not in ("exact", "sampling"):
        raise ValueError("mode must be exact or sampling")
    if type(samples) is not int or samples < 2:
        raise ValueError("At least two samples required")
    if type(max_candidates) is not int or max_candidates <= 0:
        raise ValueError("Positive max_candidates required")
    runouts = comb(remaining_count, missing)
    budget = max_attempts if max_attempts is not None else max(10000, samples*1000)
    if type(budget) is not int or budget <= 0:
        raise ValueError("Positive attempt budget required")
    config = dict(hero=card_text(hero), board=card_text(board),
                  dead_cards=card_text(dead), opponent_count=len(pools),
                  opponent_ranges=describe_pools(pools), seed=seed if mode == "sampling" else None,
                  samples=samples if mode == "sampling" else None,
                  measure="product range weights conditioned on joint legality; uniform legal runout",
                  interval="normal approximation; sampling uncertainty only",
                  assumption="all listed opponents reach showdown; equal pot shares on ties",
                  dictionary_sha256=ranker.manifest['sha256'] if isinstance(ranker, SevenCardRankDictionary) else None)

    def exact_cases():
        work = 0
        def visit(i, used, hands, weight):
            nonlocal work
            if i == len(pools):
                available = tuple(c for c in create_deck() if c not in used)
                for runout in combinations(available, missing):
                    work += 1
                    if work > max_candidates:
                        raise ExpansionLimitError("Exact joint-deal budget exceeded; use sampling or narrower ranges")
                    yield hero, board+runout, hands, weight/runouts
                return
            for hand, mass in pools[i]:
                work += 1
                if work > max_candidates:
                    raise ExpansionLimitError("Exact joint-deal budget exceeded; use sampling or narrower ranges")
                if not hand.overlaps(used):
                    yield from visit(i+1, used | set(hand.cards), hands+(hand.cards,), weight*mass)
        yield from visit(0, set(blocked), (), 1.0)

    def sample_cases():
        rng = Random(seed)
        choices = [(tuple(h for h, _ in pool), tuple(accumulate(w for _, w in pool))) for pool in pools]
        deck = create_deck()
        accepted = 0
        for _ in range(budget):
            hands = tuple(rng.choices(h, cum_weights=w)[0].cards for h, w in choices)
            used = blocked+tuple(c for h in hands for c in h)
            if len(set(used)) != len(used):
                continue
            used_set = set(used)
            remaining = [c for c in deck if c not in used_set]
            runout = tuple(rng.sample(remaining, missing))
            yield hero, board+runout, hands, 1.0
            accepted += 1
            if accepted == samples:
                return
        raise ValueError("Joint rejection budget exhausted; incompatible or very narrow ranges")

    return aggregate(exact_cases() if mode == "exact" else sample_cases(), ranker, mode, config)


def evaluate_relative_wildcards(pattern, opponent_ranges, *, dead_cards=(), card_weights=None,
                                max_candidates=1000000, ranker=None):
    """Exact general X/O/P/Q/R conditions; first 2 positions hero, next 5 board.

    Preserve hole/flop/turn/river groups. Each unique hero state is weighted once
    per legal opponent assignment. Never average board-conditioned equities equally.
    """
    parsed = WildcardPattern.parse(pattern)
    dead = cards_input(dead_cards)
    pools = range_pools(opponent_ranges, dead)
    def cases():
        work = 0
        def opponents(i, used, hands, mass, hero, board):
            nonlocal work
            if i == len(pools):
                yield hero, board, hands, mass
                return
            for hand, weight in pools[i]:
                work += 1
                if work > max_candidates:
                    raise ExpansionLimitError("Wildcard joint-deal budget exceeded; narrow the conditions")
                if not hand.overlaps(used):
                    yield from opponents(i+1, used | set(hand.cards), hands+(hand.cards,), mass*weight, hero, board)
        for cards, mass in parsed.outcomes(dead_cards=dead, card_weights=card_weights,
                                           group_sizes=(2,3,1,1), max_candidates=max_candidates):
            yield from opponents(0, set(cards+dead), (), mass, cards[:2], cards[2:])
    config = dict(pattern=parsed.normalized, group_sizes=[2,3,1,1],
                  dead_cards=card_text(dead), card_weights={str(card_id(k)): v for k, v in (card_weights or {}).items()},
                  opponent_ranges=describe_pools(pools), opponent_count=len(pools),
                  measure="hero state mass times opponent combo masses, conditioned jointly on no overlap",
                  assumption="all listed opponents reach showdown; equal pot shares on ties")
    return aggregate(cases(), ranker, "exact", config)
