from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from .actions import Action, ActionType, Street
from .cards import Card


@dataclass
class PlayerState:
    """
    1人分のプレイヤー状態。

    stack:
        現在残っているチップ。

    committed:
        現在のストリートで投入したチップ。

    total_committed:
        ハンド全体で投入したチップ。
    """

    player_id: int
    stack: int
    hole_cards: tuple[Card, Card] | None = None

    committed: int = 0
    total_committed: int = 0

    folded: bool = False
    all_in: bool = False

    def __post_init__(self) -> None:
        if self.stack < 0:
            raise ValueError("stack must be non-negative")

        if self.committed < 0:
            raise ValueError("committed must be non-negative")

        if self.total_committed < 0:
            raise ValueError("total_committed must be non-negative")

    @property
    def active(self) -> bool:
        return not self.folded

    def commit_chips(self, amount: int) -> int:
        """
        指定されたチップを投入する。

        スタックを超える場合は、残りスタックすべてを投入する。
        実際に投入した額を返す。
        """

        if amount < 0:
            raise ValueError("amount must be non-negative")

        paid = min(amount, self.stack)

        self.stack -= paid
        self.committed += paid
        self.total_committed += paid

        if self.stack == 0:
            self.all_in = True

        return paid


@dataclass(frozen=True)
class ActionRecord:
    player_index: int
    action: Action


@dataclass
class GameState:
    """
    ヘッズアップ用ゲーム状態。

    最初はリバー限定で利用する。
    """

    players: list[PlayerState]
    pot: int
    acting_player_index: int

    board: tuple[Card, ...] = field(default_factory=tuple)
    street: Street = Street.RIVER

    current_bet: int = 0
    checks_in_row: int = 0

    terminal: bool = False
    showdown: bool = False
    winner_index: int | None = None

    action_history: list[ActionRecord] = field(default_factory=list)

    def __post_init__(self) -> None:
        if len(self.players) != 2:
            raise ValueError("This GameState currently supports exactly two players.")

        if self.pot < 0:
            raise ValueError("pot must be non-negative")

        if self.acting_player_index not in {0, 1}:
            raise ValueError("acting_player_index must be 0 or 1")

        if self.street == Street.RIVER and len(self.board) != 5:
            raise ValueError("River state must contain exactly five board cards.")

    @property
    def acting_player(self) -> PlayerState:
        return self.players[self.acting_player_index]

    @property
    def opponent_index(self) -> int:
        return 1 - self.acting_player_index

    @property
    def opponent(self) -> PlayerState:
        return self.players[self.opponent_index]

    def clone(self) -> GameState:
        """
        CFRやゲーム木探索で使用する状態の複製。
        """

        return deepcopy(self)

    def to_call(self, player_index: int | None = None) -> int:
        """
        指定プレイヤーがコールするために必要な追加額。
        """

        if player_index is None:
            player_index = self.acting_player_index

        player = self.players[player_index]

        return max(0, self.current_bet - player.committed)

    def legal_actions(self) -> list[Action]:
        """
        現在のプレイヤーが選択できる行動を返す。

        現段階では以下のみを扱う。

        ・Check
        ・50% pot bet
        ・100% pot bet
        ・All-in
        ・Fold
        ・Call

        Raiseは次の段階で追加する。
        """

        if self.terminal:
            return []

        player = self.acting_player

        if player.folded or player.all_in:
            return []

        to_call = self.to_call()

        if to_call > 0:
            return [
                Action(ActionType.FOLD),
                Action(
                    ActionType.CALL,
                    amount=min(to_call, player.stack),
                ),
            ]

        actions = [Action(ActionType.CHECK)]

        bet_sizes = [
            max(1, self.pot // 2),
            max(1, self.pot),
            player.stack,
        ]

        seen_amounts: set[int] = set()

        for amount in bet_sizes:
            amount = min(amount, player.stack)

            if amount <= 0:
                continue

            if amount in seen_amounts:
                continue

            seen_amounts.add(amount)

            action_type = (
                ActionType.ALL_IN if amount == player.stack else ActionType.BET
            )

            actions.append(
                Action(
                    action_type=action_type,
                    amount=amount,
                )
            )

        return actions

    def apply_action(self, action: Action) -> None:
        """
        現在の状態にアクションを適用する。

        不正なアクションの場合はValueErrorを発生させる。
        """

        if self.terminal:
            raise ValueError("Cannot act in a terminal state.")

        legal = self.legal_actions()

        if action not in legal:
            raise ValueError(
                f"Illegal action: {action}. Legal actions: {[str(a) for a in legal]}"
            )

        actor_index = self.acting_player_index
        player = self.acting_player

        self.action_history.append(
            ActionRecord(
                player_index=actor_index,
                action=action,
            )
        )

        if action.action_type == ActionType.FOLD:
            player.folded = True
            self.terminal = True
            self.showdown = False
            self.winner_index = self.opponent_index
            self.street = Street.TERMINAL
            return

        if action.action_type == ActionType.CHECK:
            self.checks_in_row += 1

            if self.checks_in_row >= 2:
                self.terminal = True
                self.showdown = True
                self.street = Street.SHOWDOWN
                return

            self._switch_player()
            return

        if action.action_type in {
            ActionType.BET,
            ActionType.ALL_IN,
        }:
            if self.to_call() != 0:
                raise ValueError("Cannot bet while facing a bet.")

            paid = player.commit_chips(action.amount)
            self.pot += paid
            self.current_bet = player.committed
            self.checks_in_row = 0

            self._switch_player()
            return

        if action.action_type == ActionType.CALL:
            required = self.to_call()
            paid = player.commit_chips(required)

            self.pot += paid

            self.terminal = True
            self.showdown = True
            self.street = Street.SHOWDOWN
            return

        raise NotImplementedError(f"Action type not implemented: {action.action_type}")

    def _switch_player(self) -> None:
        self.acting_player_index = 1 - self.acting_player_index

    def history_string(self) -> str:
        """
        情報集合IDやデバッグに使える文字列表現。
        """

        parts = []

        for record in self.action_history:
            parts.append(f"P{record.player_index}:{record.action}")

        return "/".join(parts)
