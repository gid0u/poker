"""Simultaneous full-tree counterfactual regret matching for a tiny 3P game.

Low counterfactual regret is not a multiplayer Nash convergence certificate.
"""
from collections import defaultdict

from .response_model import TabularPolicy, info_key


class RegretSolver:
    def __init__(self, game, distribution):
        if game.board != distribution.board:
            raise ValueError("Board mismatch")
        self.game = game
        self.deals = distribution.exact()
        self.regrets = defaultdict(lambda: [0.0, 0.0])
        self.strategy_sum = defaultdict(lambda: [0.0, 0.0])
        self.iterations = 0
        self.convergence = []

    def _strategy(self, key):
        positive = [max(r, 0) for r in self.regrets[key]]
        total = sum(positive)
        return tuple(r / total for r in positive) if total else (0.5, 0.5)

    def train(self, iterations=1000, report_every=100):
        if iterations <= 0 or report_every <= 0:
            raise ValueError("Positive iteration counts required")
        for _ in range(iterations):
            updates = defaultdict(lambda: [0.0, 0.0])
            # Freeze strategies for the entire iteration, across all chance deals.
            policies = {}

            def visit(hands, chance, history=(), reach=(1.0, 1.0, 1.0)):
                actions = self.game.actions(history)
                if not actions:
                    return self.game.payoff(hands, history)
                player = len(history)
                key = info_key(player, hands[player], history)
                if key not in policies:
                    policies[key] = self._strategy(key)
                strategy = policies[key]
                children = []
                for action, p in zip(actions, strategy):
                    next_reach = list(reach)
                    next_reach[player] *= p
                    children.append(visit(hands, chance, history + (action,), tuple(next_reach)))
                value = tuple(sum(strategy[a] * children[a][i] for a in range(2)) for i in range(3))
                cf = chance
                for i in range(3):
                    if i != player:
                        cf *= reach[i]
                for a in range(2):
                    updates[key][a] += cf * (children[a][player] - value[player])
                    self.strategy_sum[key][a] += chance * reach[player] * strategy[a]
                return value

            for deal in self.deals:
                visit(deal.hands, deal.probability)
            for key, values in updates.items():
                for a in range(2):
                    self.regrets[key][a] += values[a]
            self.iterations += 1
            if self.iterations % report_every == 0 or _ == iterations - 1:
                bounds = [sum(max(0.0, max(r)) for k, r in self.regrets.items() if k[0] == p)
                          / self.iterations for p in range(3)]
                self.convergence.append(dict(iteration=self.iterations,
                                             p0_regret_bound=bounds[0], p1_regret_bound=bounds[1],
                                             p2_regret_bound=bounds[2], max_regret_bound=max(bounds)))
        return self.average_policy()

    def average_policy(self):
        return TabularPolicy({k: tuple(x / sum(v) for x in v) for k, v in self.strategy_sum.items() if sum(v)})
