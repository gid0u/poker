from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .game_state import GameState


@dataclass(frozen=True)
class ChanceOutcome:
    """
    Chance Nodeが生成する1つの初期状態。

    state:
        カード配布後のGameState。

    probability:
        この配布が選ばれる確率。

    label:
        デバッグ表示用の任意ラベル。
    """

    state: GameState
    probability: float
    label: str = ""

    def __post_init__(self) -> None:
        if self.probability < 0.0:
            raise ValueError("Chance outcome probability must not be negative.")

        if self.probability > 1.0:
            raise ValueError("Chance outcome probability must not exceed 1.0.")


@dataclass(frozen=True)
class ChanceDistribution:
    """
    複数のChanceOutcomeからなる確率分布。
    """

    outcomes: tuple[ChanceOutcome, ...]

    @classmethod
    def create(
        cls,
        outcomes: Iterable[ChanceOutcome],
    ) -> "ChanceDistribution":
        outcome_tuple = tuple(outcomes)

        if not outcome_tuple:
            raise ValueError("Chance distribution must contain at least one outcome.")

        probability_sum = sum(outcome.probability for outcome in outcome_tuple)

        if abs(probability_sum - 1.0) > 1e-9:
            raise ValueError(
                "Chance outcome probabilities must sum to 1.0. "
                f"Actual sum: {probability_sum}"
            )

        if all(outcome.probability == 0.0 for outcome in outcome_tuple):
            raise ValueError(
                "Chance distribution must contain "
                "at least one positive-probability outcome."
            )

        return cls(
            outcomes=outcome_tuple,
        )

    @classmethod
    def uniform(
        cls,
        states: Iterable[GameState],
    ) -> "ChanceDistribution":
        """
        GameState列から一様分布を作る。
        """

        state_tuple = tuple(states)

        if not state_tuple:
            raise ValueError("At least one state is required.")

        probability = 1.0 / len(state_tuple)

        return cls.create(
            ChanceOutcome(
                state=state,
                probability=probability,
            )
            for state in state_tuple
        )

    def expected_initial_pot(
        self,
    ) -> float:
        """
        初期ポットの期待値を返す。
        """

        return sum(outcome.probability * outcome.state.pot for outcome in self.outcomes)
