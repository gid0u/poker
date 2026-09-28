from __future__ import annotations

from dataclasses import dataclass, field

from .actions import Action
from .chance import ChanceDistribution
from .game_state import GameState
from .information_set import (
    InformationSet,
    InformationSetKey,
    make_information_set_key,
)
from .utility import terminal_utility


@dataclass
class CFRTrainer:
    """
    2人ゼロ和ゲーム用のCFRトレーナー。

    再帰関数の戻り値は常にP0視点の利得。

    information_sets:
        情報集合ごとの累積後悔値と累積戦略。

    iterations_completed:
        完了した学習反復数。

    utility_sum:
        各反復のP0期待利得の合計。
    """

    information_sets: dict[
        InformationSetKey,
        InformationSet,
    ] = field(default_factory=dict)

    iterations_completed: int = 0
    utility_sum: float = 0.0

    def train(
        self,
        initial_state: GameState,
        iterations: int,
    ) -> float:
        """
        単一の固定初期状態についてCFRを実行する。

        従来互換用のメソッド。
        内部では確率1.0のChanceDistributionとして処理する。
        """

        distribution = ChanceDistribution.uniform([initial_state])

        return self.train_distribution(
            distribution=distribution,
            iterations=iterations,
        )

    def train_distribution(
        self,
        distribution: ChanceDistribution,
        iterations: int,
    ) -> float:
        """
        複数のカード配布を持つ確率分布についてCFRを実行する。

        1反復の中で全ChanceOutcomeを走査する。
        各配布の後悔値と平均戦略は、
        その配布確率で重み付けされる。

        戻り値は、今回実行した反復における
        P0視点の平均期待利得。
        """

        if iterations <= 0:
            raise ValueError("iterations must be greater than zero.")

        run_utility_sum = 0.0

        for _ in range(iterations):
            iteration_utility = 0.0

            for outcome in distribution.outcomes:
                if outcome.probability == 0.0:
                    continue

                state = outcome.state.clone()

                outcome_utility = self.cfr(
                    state=state,
                    reach_probabilities=(1.0, 1.0),
                    chance_reach=outcome.probability,
                )

                iteration_utility += outcome.probability * outcome_utility

            run_utility_sum += iteration_utility
            self.utility_sum += iteration_utility
            self.iterations_completed += 1

        return run_utility_sum / iterations

    def cfr(
        self,
        state: GameState,
        reach_probabilities: tuple[float, float],
        chance_reach: float = 1.0,
    ) -> float:
        """
        CFRの再帰処理。

        reach_probabilities:
            各プレイヤー自身の戦略による到達確率。

        chance_reach:
            Chance Nodeによって現在のカード配布へ
            到達した確率。

        戻り値:
            P0視点の期待利得。
        """

        self._validate_reach_probabilities(reach_probabilities)

        self._validate_chance_reach(chance_reach)

        if state.terminal:
            return terminal_utility(
                state,
                player_index=0,
            )

        acting_player = state.acting_player_index

        if acting_player not in (0, 1):
            raise ValueError(
                "CFRTrainer supports exactly two players. "
                f"Invalid acting player: {acting_player}"
            )

        legal_actions = tuple(state.legal_actions())

        if not legal_actions:
            raise ValueError("Non-terminal state has no legal actions.")

        information_set = self._get_or_create_information_set(
            state=state,
            legal_actions=legal_actions,
        )

        strategy = information_set.current_strategy()

        own_reach = reach_probabilities[acting_player]

        information_set.accumulate_strategy(
            strategy=strategy,
            realization_weight=(chance_reach * own_reach),
        )

        action_utilities: dict[
            Action,
            float,
        ] = {}

        node_utility = 0.0

        for action in legal_actions:
            child_state = state.clone()
            child_state.apply_action(action)

            child_reach = list(reach_probabilities)

            child_reach[acting_player] *= strategy[action]

            action_utility = self.cfr(
                state=child_state,
                reach_probabilities=(
                    child_reach[0],
                    child_reach[1],
                ),
                chance_reach=chance_reach,
            )

            action_utilities[action] = action_utility

            node_utility += strategy[action] * action_utility

        opponent = 1 - acting_player

        opponent_reach = reach_probabilities[opponent]

        counterfactual_reach = chance_reach * opponent_reach

        for action in legal_actions:
            if acting_player == 0:
                immediate_regret = action_utilities[action] - node_utility
            else:
                immediate_regret = node_utility - action_utilities[action]

            weighted_regret = counterfactual_reach * immediate_regret

            information_set.add_regret(
                action=action,
                regret=weighted_regret,
            )

        return node_utility

    def get_information_set(
        self,
        key: InformationSetKey,
    ) -> InformationSet | None:
        return self.information_sets.get(key)

    def average_strategy_for_state(
        self,
        state: GameState,
    ) -> dict[Action, float]:
        if state.terminal:
            raise ValueError("Terminal states do not have strategies.")

        key = make_information_set_key(state)

        information_set = self.information_sets.get(key)

        if information_set is None:
            raise ValueError(
                "No information set has been trained for the supplied state."
            )

        return information_set.average_strategy()

    def current_strategy_for_state(
        self,
        state: GameState,
    ) -> dict[Action, float]:
        if state.terminal:
            raise ValueError("Terminal states do not have strategies.")

        key = make_information_set_key(state)

        information_set = self.information_sets.get(key)

        if information_set is None:
            raise ValueError(
                "No information set has been trained for the supplied state."
            )

        return information_set.current_strategy()

    def overall_average_utility(
        self,
    ) -> float:
        if self.iterations_completed == 0:
            return 0.0

        return self.utility_sum / self.iterations_completed

    def reset(
        self,
    ) -> None:
        self.information_sets.clear()
        self.iterations_completed = 0
        self.utility_sum = 0.0

    def _get_or_create_information_set(
        self,
        state: GameState,
        legal_actions: tuple[Action, ...],
    ) -> InformationSet:
        key = make_information_set_key(state)

        information_set = self.information_sets.get(key)

        if information_set is None:
            information_set = InformationSet.create(
                key=key,
                actions=legal_actions,
            )

            self.information_sets[key] = information_set

            return information_set

        if information_set.actions != legal_actions:
            raise ValueError(
                "The same information set key produced different legal actions."
            )

        return information_set

    @staticmethod
    def _validate_reach_probabilities(
        reach_probabilities: tuple[
            float,
            float,
        ],
    ) -> None:
        if len(reach_probabilities) != 2:
            raise ValueError("Exactly two reach probabilities are required.")

        for probability in reach_probabilities:
            if probability < 0.0:
                raise ValueError("Reach probabilities must not be negative.")

            if probability > 1.0:
                raise ValueError("Reach probabilities must not exceed 1.0.")

    @staticmethod
    def _validate_chance_reach(
        chance_reach: float,
    ) -> None:
        if chance_reach < 0.0:
            raise ValueError("chance_reach must not be negative.")

        if chance_reach > 1.0:
            raise ValueError("chance_reach must not exceed 1.0.")


def format_strategy(
    strategy: dict[Action, float],
    decimals: int = 4,
) -> str:
    if decimals < 0:
        raise ValueError("decimals must not be negative.")

    return ", ".join(
        f"{action}={probability:.{decimals}f}"
        for action, probability in strategy.items()
    )


def format_average_strategies(
    trainer: CFRTrainer,
    decimals: int = 4,
) -> str:
    if decimals < 0:
        raise ValueError("decimals must not be negative.")

    lines: list[str] = []

    sorted_items = sorted(
        trainer.information_sets.items(),
        key=lambda item: str(item[0]),
    )

    for key, information_set in sorted_items:
        strategy_text = format_strategy(
            information_set.average_strategy(),
            decimals=decimals,
        )

        lines.append(f"{key}: {strategy_text}")

    return "\n".join(lines)
