from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Street(Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    TERMINAL = "terminal"


class ActionType(Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


@dataclass(frozen=True)
class Action:
    """
    プレイヤーが選択するアクション。

    amountは、このアクションによって追加で投入するチップ数。
    CHECKやFOLDでは0。
    """

    action_type: ActionType
    amount: int = 0

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount must be non-negative")

        if (
            self.action_type
            in {
                ActionType.FOLD,
                ActionType.CHECK,
            }
            and self.amount != 0
        ):
            raise ValueError(f"{self.action_type.value} action must have amount=0")

    def __str__(self) -> str:
        if self.amount:
            return f"{self.action_type.value}({self.amount})"

        return self.action_type.value
