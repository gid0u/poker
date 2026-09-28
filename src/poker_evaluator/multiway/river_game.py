from dataclasses import dataclass
from functools import lru_cache
from math import isfinite

from ..evaluate7 import evaluate7
from .deal_distribution import normalize_board


@lru_cache(maxsize=100000)
def hand_value(board, hand):
    return evaluate7(list(board + hand.cards))


@dataclass(frozen=True)
class RiverGame:
    board: tuple
    pot: float = 100
    bet: float = 50
    stacks: tuple = (100, 100, 100)

    def __post_init__(self):
        object.__setattr__(self, "board", normalize_board(self.board))
        if not isfinite(self.pot) or self.pot < 0 or not isfinite(self.bet) or self.bet <= 0:
            raise ValueError("Invalid pot or bet")
        if len(self.stacks) != 3 or any(not isfinite(s) or s < self.bet for s in self.stacks):
            raise ValueError("All three stacks must cover the fixed bet; no side pots")

    def actions(self, history=()):
        if history == ():
            return ("check", "bet")
        if history == ("bet",) or history in (("bet", "fold"), ("bet", "call")):
            return ("fold", "call")
        if history == ("check",) or (len(history) == 3 and history[0] == "bet"
                                               and all(a in ("fold", "call") for a in history[1:])):
            return ()
        raise ValueError("Invalid history")

    def payoff(self, hands, history):
        if self.actions(history):
            raise ValueError("Payoff requires a terminal history")
        cards = self.board + tuple(c for h in hands for c in h.cards)
        if len(hands) != 3 or len(set(cards)) != 11:
            raise ValueError("Illegal deal")
        contributions = [0.0] * 3
        active = [0, 1, 2]
        if history[0] == "bet":
            active = [0] + [i for i in (1, 2) if history[i] == "call"]
            contributions = [self.bet if i in active else 0.0 for i in range(3)]
        best = max(hand_value(self.board, hands[i]) for i in active)
        winners = [i for i in active if hand_value(self.board, hands[i]) == best]
        share = (self.pot + sum(contributions)) / len(winners)
        return tuple((share if i in winners else 0) - contributions[i] for i in range(3))
