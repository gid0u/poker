from __future__ import annotations

from .evaluate7 import evaluate7
from .game_state import GameState


def terminal_utility(
    state: GameState,
    player_index: int,
) -> float:
    """
    終端状態における指定プレイヤーの純利得を返す。

    現在はヘッズアップ・リバー限定のGameStateを対象とする。

    利得の基準:
        リバー開始時点のポットを、両プレイヤーが半分ずつ
        保有していたものとして計算する。

    これにより、常に次が成立する。

        utility(player_0) + utility(player_1) == 0

    計算式:
        純利得
        = 終端で受け取るチップ
        - リバーで追加投入したチップ
        - 初期ポットの基準持分

    Args:
        state:
            終端状態のGameState。

        player_index:
            利得を計算するプレイヤー。
            現在は0または1。

    Returns:
        指定プレイヤーの純利得。

    Raises:
        ValueError:
            プレイヤー番号が不正な場合。
            状態が終端でない場合。
            ショーダウンに必要なカードがない場合。
            ポット情報に矛盾がある場合。
    """

    if player_index not in {0, 1}:
        raise ValueError("player_index must be 0 or 1")

    if not state.terminal:
        raise ValueError("Utility can only be calculated for a terminal state.")

    initial_pot = _calculate_initial_pot(state)
    baseline_share = initial_pot / 2.0

    payouts = _calculate_terminal_payouts(
        state=state,
        initial_pot=initial_pot,
    )

    player = state.players[player_index]

    return float(payouts[player_index] - player.total_committed - baseline_share)


def _calculate_initial_pot(state: GameState) -> float:
    """
    リバー開始時点のポットを逆算する。

    現在のGameStateではtotal_committedが
    リバー開始後の追加投入額を表しているため、

        初期ポット
        = 現在のポット - 両者の追加投入額

    として求められる。
    """

    added_chips = sum(player.total_committed for player in state.players)

    initial_pot = state.pot - added_chips

    if initial_pot < 0:
        raise ValueError("Invalid pot state: total committed chips exceed the pot.")

    return float(initial_pot)


def _calculate_terminal_payouts(
    state: GameState,
    initial_pot: float,
) -> tuple[float, float]:
    """
    終端状態で各プレイヤーが受け取るチップを計算する。

    フォールド終端:
        勝者がポット全額を受け取る。

    ショーダウン:
        両者の投入額が異なる場合、超過した未コール分を
        投入したプレイヤーへ返却してから勝敗を処理する。

    Returns:
        (player_0の受取額, player_1の受取額)
    """

    if not state.showdown:
        return _fold_payouts(state)

    return _showdown_payouts(
        state=state,
        initial_pot=initial_pot,
    )


def _fold_payouts(
    state: GameState,
) -> tuple[float, float]:
    """
    フォールドによる終端の受取額を返す。
    """

    if state.winner_index not in {0, 1}:
        raise ValueError("A non-showdown terminal state must have a winner.")

    payouts = [0.0, 0.0]
    payouts[state.winner_index] = float(state.pot)

    return payouts[0], payouts[1]


def _showdown_payouts(
    state: GameState,
    initial_pot: float,
) -> tuple[float, float]:
    """
    ショーダウン時の受取額を返す。

    ショートスタックによる不完全なコールにも対応する。

    例:
        P0が100ベット
        P1が残り60をコール

    この場合、P0の超過40は未コール分としてP0へ返却する。
    """

    player_0 = state.players[0]
    player_1 = state.players[1]

    if player_0.hole_cards is None:
        raise ValueError("Player 0 has no hole cards for showdown.")

    if player_1.hole_cards is None:
        raise ValueError("Player 1 has no hole cards for showdown.")

    if len(state.board) != 5:
        raise ValueError("River showdown requires exactly five board cards.")

    contribution_0 = player_0.total_committed
    contribution_1 = player_1.total_committed

    matched_contribution = min(
        contribution_0,
        contribution_1,
    )

    refund_0 = max(
        contribution_0 - matched_contribution,
        0,
    )
    refund_1 = max(
        contribution_1 - matched_contribution,
        0,
    )

    contested_pot = initial_pot + 2 * matched_contribution

    player_0_rank = evaluate7(list(player_0.hole_cards) + list(state.board))

    player_1_rank = evaluate7(list(player_1.hole_cards) + list(state.board))

    if player_0_rank > player_1_rank:
        return (
            float(contested_pot + refund_0),
            float(refund_1),
        )

    if player_1_rank > player_0_rank:
        return (
            float(refund_0),
            float(contested_pot + refund_1),
        )

    split_share = contested_pot / 2.0

    return (
        float(split_share + refund_0),
        float(split_share + refund_1),
    )
