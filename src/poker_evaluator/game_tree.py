from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

from .actions import Action
from .game_state import GameState


@dataclass
class GameTreeNode:
    """
    ゲーム木の1ノード。

    state:
        このノードが表すゲーム状態。

    action_from_parent:
        親ノードからこのノードへ到達するために
        選択されたアクション。
        ルートノードではNone。

    children:
        この状態から到達可能な子ノード。
    """

    state: GameState
    action_from_parent: Action | None = None
    children: list["GameTreeNode"] = field(default_factory=list)

    @property
    def is_terminal(self) -> bool:
        """終端状態かどうかを返す。"""

        return self.state.terminal

    @property
    def is_leaf(self) -> bool:
        """子ノードを持たない葉ノードかどうかを返す。"""

        return len(self.children) == 0

    @property
    def depth(self) -> int:
        """
        このプロパティ単体では親を保持していないため、
        深さは計算しない。

        木全体の深さにはmax_depth()を使用する。
        """

        raise AttributeError(
            "GameTreeNode does not store its parent. "
            "Use max_depth() to inspect tree depth."
        )


def expand_state(
    state: GameState,
) -> Iterator[tuple[Action, GameState]]:
    """
    現在の状態から、合法アクションと次状態を列挙する。

    元のstateは変更しない。
    各子状態はclone()で独立した状態として生成される。

    Yields:
        (action, child_state)
    """

    if state.terminal:
        return

    for action in state.legal_actions():
        child_state = state.clone()
        child_state.apply_action(action)

        yield action, child_state


def build_game_tree(
    state: GameState,
) -> GameTreeNode:
    """
    指定状態から終端までのゲーム木を再帰的に構築する。

    元のstateは変更しない。
    """

    root = GameTreeNode(
        state=state.clone(),
    )

    _build_children(root)

    return root


def _build_children(
    node: GameTreeNode,
) -> None:
    """
    指定ノード以下の子ノードを再帰的に構築する。
    """

    if node.state.terminal:
        return

    for action, child_state in expand_state(node.state):
        child_node = GameTreeNode(
            state=child_state,
            action_from_parent=action,
        )

        node.children.append(child_node)
        _build_children(child_node)


def iter_nodes(
    root: GameTreeNode,
) -> Iterator[GameTreeNode]:
    """
    ゲーム木の全ノードを深さ優先で列挙する。

    ルートノード自身も含む。
    """

    yield root

    for child in root.children:
        yield from iter_nodes(child)


def iter_leaf_nodes(
    root: GameTreeNode,
) -> Iterator[GameTreeNode]:
    """
    葉ノードだけを列挙する。
    """

    for node in iter_nodes(root):
        if node.is_leaf:
            yield node


def iter_terminal_nodes(
    root: GameTreeNode,
) -> Iterator[GameTreeNode]:
    """
    終端状態のノードだけを列挙する。
    """

    for node in iter_nodes(root):
        if node.is_terminal:
            yield node


def count_nodes(
    root: GameTreeNode,
) -> int:
    """
    ゲーム木の全ノード数を返す。
    """

    return sum(1 for _ in iter_nodes(root))


def count_leaf_nodes(
    root: GameTreeNode,
) -> int:
    """
    ゲーム木の葉ノード数を返す。
    """

    return sum(1 for _ in iter_leaf_nodes(root))


def count_terminal_nodes(
    root: GameTreeNode,
) -> int:
    """
    ゲーム木の終端ノード数を返す。
    """

    return sum(1 for _ in iter_terminal_nodes(root))


def max_depth(
    root: GameTreeNode,
) -> int:
    """
    ゲーム木の最大深さを返す。

    ルートだけの場合は0。
    ルートから子への1回の遷移を深さ1とする。
    """

    if root.is_leaf:
        return 0

    return 1 + max(max_depth(child) for child in root.children)


def action_paths(
    root: GameTreeNode,
) -> list[tuple[Action, ...]]:
    """
    ルートから各終端ノードまでのアクション列を返す。

    CFRの動作確認やデバッグに利用できる。
    """

    paths: list[tuple[Action, ...]] = []

    def walk(
        node: GameTreeNode,
        current_path: tuple[Action, ...],
    ) -> None:
        if node.is_terminal:
            paths.append(current_path)
            return

        for child in node.children:
            if child.action_from_parent is None:
                raise ValueError("A non-root child must have action_from_parent.")

            walk(
                child,
                current_path + (child.action_from_parent,),
            )

    walk(root, tuple())

    return paths


def format_action_path(
    path: tuple[Action, ...],
) -> str:
    """
    アクション列を読みやすい文字列へ変換する。
    """

    return " -> ".join(str(action) for action in path)


def format_game_tree(
    root: GameTreeNode,
) -> str:
    """
    ゲーム木全体をインデント付き文字列で返す。

    主にデバッグ表示用。
    """

    lines: list[str] = []

    def walk(
        node: GameTreeNode,
        depth: int,
    ) -> None:
        indent = "  " * depth

        if node.action_from_parent is None:
            label = "ROOT"
        else:
            label = str(node.action_from_parent)

        status_parts = [
            f"pot={node.state.pot}",
            f"actor=P{node.state.acting_player_index}",
        ]

        if node.state.terminal:
            status_parts.append("terminal")

        if node.state.showdown:
            status_parts.append("showdown")

        if node.state.winner_index is not None:
            status_parts.append(f"winner=P{node.state.winner_index}")

        status = ", ".join(status_parts)

        lines.append(f"{indent}{label} [{status}]")

        for child in node.children:
            walk(
                child,
                depth + 1,
            )

    walk(root, 0)

    return "\n".join(lines)
