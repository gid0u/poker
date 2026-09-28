from math import sqrt, isfinite
from statistics import variance

from ..action_ev import ActionEV


def probabilities(policy, player, hand, history):
    p = policy.probabilities(player, hand, history)
    if len(p) != 2 or any(not isfinite(x) or x < 0 for x in p) or abs(sum(p) - 1) > 1e-9:
        raise ValueError("Invalid policy probabilities")
    return p


class MultiwayMonteCarloEngine:
    def __init__(self, game, distribution):
        if game.board != distribution.board:
            raise ValueError("Game and distribution boards differ")
        self.game, self.distribution = game, distribution

    def _reach(self, hands, history, policy):
        reach = 1.0
        for i, action in enumerate(history):
            actions = self.game.actions(history[:i])
            reach *= probabilities(policy, i, hands[i], history[:i])[actions.index(action)]
        return reach

    def _value(self, hands, history, player, policy):
        actions = self.game.actions(history)
        if not actions:
            return self.game.payoff(hands, history)[player]
        actor = len(history)
        probs = probabilities(policy, actor, hands[actor], history)
        return sum(p * self._value(hands, history + (a,), player, policy)
                   for a, p in zip(actions, probs))

    def evaluate(self, policy, *, history=(), hand=None, mode="sampling", samples=10000,
                 seed=0, bb=None, max_attempts=None):
        history = tuple(history)
        actions = self.game.actions(history)
        if not actions:
            raise ValueError("Cannot evaluate a terminal node")
        player = len(history)
        if bb is not None and (not isfinite(bb) or bb <= 0):
            raise ValueError("bb must be positive")
        distribution = self.distribution
        if hand is not None:
            from .deal_distribution import MultiwayDealDistribution, WeightedRange
            if not any(c.normalized() == hand.normalized() for c, _ in distribution.ranges[player].entries):
                raise ValueError("Hand outside acting player's range")
            ranges = list(distribution.ranges)
            ranges[player] = WeightedRange.from_range([hand])
            distribution = MultiwayDealDistribution(ranges, distribution.board)
        if mode == "exact":
            rows = [(d, d.probability * self._reach(d.hands, history, policy)) for d in distribution.exact()]
            mass = sum(w for _, w in rows)
            if mass <= 0:
                raise ValueError("History has zero reach")
            rows = [(d, w / mass) for d, w in rows if w]
        elif mode in ("sample", "sampling"):
            if not isinstance(samples, int) or samples < 2:
                raise ValueError("At least two samples required for standard error")
            from .deal_distribution import MultiwayDealDistribution, WeightedRange
            ranges = list(distribution.ranges)
            # Given public history, each observed action likelihood depends only
            # on that actor's private hand. Reweight before collision rejection:
            # this is the exact posterior, without rare-history rejection costs.
            for actor, action in enumerate(history):
                index = self.game.actions(history[:actor]).index(action)
                ranges[actor] = WeightedRange(tuple(
                    (combo, weight * probabilities(policy, actor, combo, history[:actor])[index])
                    for combo, weight in ranges[actor].entries))
            posterior = MultiwayDealDistribution(ranges, distribution.board)
            accepted = posterior.sample(samples, seed, max_attempts)
            rows = [(d, 1 / samples) for d in accepted]
        else:
            raise ValueError("mode must be exact or sampling")
        results = []
        for action in actions:
            values = [self._value(d.hands, history + (action,), player, policy) for d, _ in rows]
            ev = sum(v * w for v, (_, w) in zip(values, rows))
            se = 0.0 if mode == "exact" else sqrt(variance(values) / len(values))
            results.append(ActionEV(action, ev, ev / bb if bb else None, se, len(rows),
                                    source=mode, ci95_low=ev - 1.96 * se, ci95_high=ev + 1.96 * se))
        return tuple(results)
