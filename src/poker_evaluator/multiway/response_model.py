from dataclasses import dataclass
from math import isfinite


def info_key(player, hand, history):
    return player, tuple(sorted(hand.cards)), tuple(history)


@dataclass(frozen=True)
class SequentialResponseModel:
    p1_call: float = 0.5
    p2_call_after_fold: float = 0.5
    p2_call_after_call: float = 0.5

    def __post_init__(self):
        if any(not isfinite(p) or not 0 <= p <= 1 for p in (
                self.p1_call, self.p2_call_after_fold, self.p2_call_after_call)):
            raise ValueError("Call probabilities must lie in [0,1]")

    def probabilities(self, player, hand, history):
        if player == 0 and history == ():
            return (0.5, 0.5)
        if player == 1 and history == ("bet",):
            p = self.p1_call
        elif player == 2 and history in (("bet", "fold"), ("bet", "call")):
            p = self.p2_call_after_call if history[-1] == "call" else self.p2_call_after_fold
        else:
            raise ValueError("Invalid response information set")
        return 1 - p, p


@dataclass
class TabularPolicy:
    table: dict

    def probabilities(self, player, hand, history):
        return self.table.get(info_key(player, hand, history), (0.5, 0.5))
