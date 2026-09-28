from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .actions import Action
from .game_state import GameState


@dataclass(frozen=True)
class InformationSetKey:
    """
    CFRで使用する情報集合キー。

    同じプレイヤーから見て区別できない状態は、
    同じInformationSetKeyになる。

    相手のホールカードは含めない。
    """

    player_index: int
    hole_cards: tuple[str, ...]
    board: tuple[str, ...]
    action_history: tuple[str, ...]
    pot: int
    stacks: tuple[int, ...]
    committed: tuple[int, ...]
    to_call: int

    def __str__(self) -> str:
        """
        情報集合キーを読みやすい文字列に変換する。
        """

        hole_cards_text = "".join(self.hole_cards)

        board_text = "".join(self.board)

        if self.action_history:
            history_text = "-".join(self.action_history)
        else:
            history_text = "root"

        stacks_text = ",".join(str(stack) for stack in self.stacks)

        committed_text = ",".join(str(amount) for amount in self.committed)

        return (
            f"P{self.player_index}"
            f"|hole={hole_cards_text}"
            f"|board={board_text}"
            f"|history={history_text}"
            f"|pot={self.pot}"
            f"|stacks={stacks_text}"
            f"|committed={committed_text}"
            f"|call={self.to_call}"
        )


@dataclass
class InformationSet:
    """
    1つの情報集合に保存するCFR用データ。

    regrets:
        各アクションの累積後悔値。

    strategy_sum:
        平均戦略を計算するための累積戦略値。

    visits:
        この情報集合で戦略を累積した回数。
    """

    key: InformationSetKey
    actions: tuple[Action, ...]
    regrets: dict[Action, float]
    strategy_sum: dict[Action, float]
    visits: int = 0

    @classmethod
    def create(
        cls,
        key: InformationSetKey,
        actions: Iterable[Action],
    ) -> "InformationSet":
        """
        合法アクション列から情報集合を作成する。
        """

        action_tuple = tuple(actions)

        if not action_tuple:
            raise ValueError("An information set must have at least one action.")

        if len(set(action_tuple)) != len(action_tuple):
            raise ValueError("Information set actions must be unique.")

        return cls(
            key=key,
            actions=action_tuple,
            regrets={action: 0.0 for action in action_tuple},
            strategy_sum={action: 0.0 for action in action_tuple},
            visits=0,
        )

    def current_strategy(
        self,
    ) -> dict[Action, float]:
        """
        Regret Matchingによる現在戦略を返す。

        正の後悔値だけを使用する。

        正の後悔値が1つもない場合は、
        全合法アクションを等確率にする。
        """

        positive_regrets = {
            action: max(
                self.regrets[action],
                0.0,
            )
            for action in self.actions
        }

        positive_sum = sum(positive_regrets.values())

        if positive_sum > 0.0:
            return {
                action: (positive_regrets[action] / positive_sum)
                for action in self.actions
            }

        uniform_probability = 1.0 / len(self.actions)

        return {action: uniform_probability for action in self.actions}

    def accumulate_strategy(
        self,
        strategy: dict[Action, float],
        realization_weight: float = 1.0,
    ) -> None:
        """
        平均戦略計算用に戦略を累積する。

        realization_weightは、
        そのプレイヤー自身の到達確率。
        """

        if realization_weight < 0.0:
            raise ValueError("realization_weight must not be negative.")

        _validate_strategy(
            actions=self.actions,
            strategy=strategy,
        )

        for action in self.actions:
            self.strategy_sum[action] += realization_weight * strategy[action]

        self.visits += 1

    def average_strategy(
        self,
    ) -> dict[Action, float]:
        """
        累積された平均戦略を返す。

        戦略がまだ累積されていない場合は、
        等確率戦略を返す。
        """

        total = sum(self.strategy_sum.values())

        if total > 0.0:
            return {
                action: (self.strategy_sum[action] / total) for action in self.actions
            }

        uniform_probability = 1.0 / len(self.actions)

        return {action: uniform_probability for action in self.actions}

    def add_regret(
        self,
        action: Action,
        regret: float,
    ) -> None:
        """
        指定アクションの累積後悔値を更新する。
        """

        if action not in self.regrets:
            raise ValueError(f"Unknown action for information set: {action}")

        self.regrets[action] += regret


def make_information_set_key(
    state: GameState,
    player_index: int | None = None,
) -> InformationSetKey:
    """
    GameStateから情報集合キーを生成する。

    player_indexを省略した場合は、
    現在の行動プレイヤーを使用する。

    相手のホールカードはキーに含めない。
    """

    if player_index is None:
        player_index = state.acting_player_index

    if not 0 <= player_index < len(state.players):
        raise ValueError(f"Invalid player index: {player_index}")

    player = state.players[player_index]

    hole_cards = getattr(
        player,
        "hole_cards",
        None,
    )

    if hole_cards is None:
        hole_card_strings: tuple[str, ...] = tuple()
    else:
        hole_card_strings = tuple(_format_card(card) for card in hole_cards)

    board_strings = tuple(_format_card(card) for card in state.board)

    action_history = tuple(
        _format_action_record(record) for record in state.action_history
    )

    stacks = tuple(player_state.stack for player_state in state.players)

    committed = tuple(player_state.total_committed for player_state in state.players)

    return InformationSetKey(
        player_index=player_index,
        hole_cards=hole_card_strings,
        board=board_strings,
        action_history=action_history,
        pot=state.pot,
        stacks=stacks,
        committed=committed,
        to_call=state.to_call(),
    )


def make_information_set(
    state: GameState,
) -> InformationSet:
    """
    現在のGameStateからInformationSetを作成する。

    終端状態には意思決定が存在しないため、
    InformationSetは作成できない。
    """

    if state.terminal:
        raise ValueError("Cannot create an information set from a terminal state.")

    actions = tuple(state.legal_actions())

    if not actions:
        raise ValueError("Non-terminal state has no legal actions.")

    key = make_information_set_key(state)

    return InformationSet.create(
        key=key,
        actions=actions,
    )


def _format_card(
    card: object,
) -> str:
    """
    CardをAh、Ks、Tdのような形式に変換する。

    rank:
        2から14を想定する。
        14=A、13=K、12=Q、11=J、10=T。

    suit:
        現在のCard実装に合わせて、
        0=s、1=c、2=h、3=dとして扱う。

    Card形式でないオブジェクトの場合は、
    通常のstr()へフォールバックする。
    """

    rank = getattr(
        card,
        "rank",
        None,
    )

    suit = getattr(
        card,
        "suit",
        None,
    )

    if rank is None or suit is None:
        return str(card)

    rank_symbols = {
        14: "A",
        13: "K",
        12: "Q",
        11: "J",
        10: "T",
    }

    suit_symbols = {
        0: "s",
        1: "c",
        2: "h",
        3: "d",
    }

    rank_text = rank_symbols.get(
        rank,
        str(rank),
    )

    suit_text = suit_symbols.get(
        suit,
    )

    if suit_text is None:
        return str(card)

    return f"{rank_text}{suit_text}"


def _format_action_record(
    record: object,
) -> str:
    """
    ActionRecordまたはActionを行動文字列に変換する。

    ActionRecordの場合はrecord.actionを使用する。
    Actionが直接渡された場合はそのまま使用する。
    """

    action = getattr(
        record,
        "action",
        record,
    )

    return str(action)


def _validate_strategy(
    actions: tuple[Action, ...],
    strategy: dict[Action, float],
) -> None:
    """
    戦略辞書が合法アクション上の
    正しい確率分布になっているか確認する。
    """

    expected_actions = set(actions)

    actual_actions = set(strategy)

    if actual_actions != expected_actions:
        raise ValueError("Strategy actions do not match the information set actions.")

    for action, probability in strategy.items():
        if probability < 0.0:
            raise ValueError(
                f"Negative strategy probability for {action}: {probability}"
            )

    probability_sum = sum(strategy.values())

    if abs(probability_sum - 1.0) > 1e-9:
        raise ValueError(
            f"Strategy probabilities must sum to 1.0. Actual sum: {probability_sum}"
        )
