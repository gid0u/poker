import unittest

from poker_evaluator.actions import (
    Action,
    ActionType,
    Street,
)
from poker_evaluator.cards import parse_card
from poker_evaluator.game_state import (
    GameState,
    PlayerState,
)
from poker_evaluator.game_tree import (
    action_paths,
    build_game_tree,
    count_leaf_nodes,
    count_nodes,
    count_terminal_nodes,
    expand_state,
    format_action_path,
    format_game_tree,
    iter_leaf_nodes,
    iter_nodes,
    iter_terminal_nodes,
    max_depth,
)


def make_river_state() -> GameState:
    """
    ゲーム木テスト用のリバー開始状態。

    P0:
        Kh Qh

    P1:
        As Jc

    Board:
        Ks 8h 7d 3c 2s

    ショーダウンではP0のKワンペアが
    P1のAハイに勝つ。
    """

    return GameState(
        players=[
            PlayerState(
                player_id=0,
                stack=100,
                hole_cards=(
                    parse_card("Kh"),
                    parse_card("Qh"),
                ),
            ),
            PlayerState(
                player_id=1,
                stack=100,
                hole_cards=(
                    parse_card("As"),
                    parse_card("Jc"),
                ),
            ),
        ],
        pot=100,
        acting_player_index=0,
        board=tuple(
            parse_card(card)
            for card in [
                "Ks",
                "8h",
                "7d",
                "3c",
                "2s",
            ]
        ),
        street=Street.RIVER,
    )


class TestExpandState(unittest.TestCase):
    def test_expand_state_returns_all_initial_actions(
        self,
    ) -> None:
        state = make_river_state()

        branches = list(expand_state(state))

        actions = [action for action, _ in branches]

        self.assertEqual(
            actions,
            [
                Action(ActionType.CHECK),
                Action(
                    ActionType.BET,
                    amount=50,
                ),
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ),
            ],
        )

    def test_expand_state_does_not_modify_original(
        self,
    ) -> None:
        state = make_river_state()

        original_pot = state.pot
        original_stack_0 = state.players[0].stack
        original_stack_1 = state.players[1].stack
        original_actor = state.acting_player_index

        list(expand_state(state))

        self.assertEqual(
            state.pot,
            original_pot,
        )
        self.assertEqual(
            state.players[0].stack,
            original_stack_0,
        )
        self.assertEqual(
            state.players[1].stack,
            original_stack_1,
        )
        self.assertEqual(
            state.acting_player_index,
            original_actor,
        )
        self.assertEqual(
            state.action_history,
            [],
        )
        self.assertFalse(state.terminal)

    def test_child_states_are_independent(
        self,
    ) -> None:
        state = make_river_state()

        branches = list(expand_state(state))

        check_state = branches[0][1]
        bet_state = branches[1][1]
        all_in_state = branches[2][1]

        self.assertEqual(
            check_state.pot,
            100,
        )
        self.assertEqual(
            bet_state.pot,
            150,
        )
        self.assertEqual(
            all_in_state.pot,
            200,
        )

        bet_state.players[0].stack = 1

        self.assertEqual(
            state.players[0].stack,
            100,
        )
        self.assertEqual(
            check_state.players[0].stack,
            100,
        )
        self.assertEqual(
            all_in_state.players[0].stack,
            0,
        )

    def test_check_branch_switches_player(
        self,
    ) -> None:
        state = make_river_state()

        branches = dict(expand_state(state))

        check_state = branches[Action(ActionType.CHECK)]

        self.assertEqual(
            check_state.acting_player_index,
            1,
        )
        self.assertFalse(check_state.terminal)
        self.assertEqual(
            check_state.checks_in_row,
            1,
        )

    def test_bet_branch_updates_state(
        self,
    ) -> None:
        state = make_river_state()

        branches = dict(expand_state(state))

        bet_state = branches[
            Action(
                ActionType.BET,
                amount=50,
            )
        ]

        self.assertEqual(
            bet_state.pot,
            150,
        )
        self.assertEqual(
            bet_state.players[0].stack,
            50,
        )
        self.assertEqual(
            bet_state.players[0].total_committed,
            50,
        )
        self.assertEqual(
            bet_state.acting_player_index,
            1,
        )
        self.assertEqual(
            bet_state.to_call(),
            50,
        )
        self.assertFalse(bet_state.terminal)

    def test_all_in_branch_updates_state(
        self,
    ) -> None:
        state = make_river_state()

        branches = dict(expand_state(state))

        all_in_state = branches[
            Action(
                ActionType.ALL_IN,
                amount=100,
            )
        ]

        self.assertEqual(
            all_in_state.pot,
            200,
        )
        self.assertEqual(
            all_in_state.players[0].stack,
            0,
        )
        self.assertEqual(
            all_in_state.players[0].total_committed,
            100,
        )
        self.assertEqual(
            all_in_state.acting_player_index,
            1,
        )
        self.assertEqual(
            all_in_state.to_call(),
            100,
        )
        self.assertFalse(all_in_state.terminal)

    def test_terminal_state_has_no_branches(
        self,
    ) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        self.assertTrue(state.terminal)
        self.assertEqual(
            list(expand_state(state)),
            [],
        )


class TestBuildGameTree(unittest.TestCase):
    def test_build_tree_does_not_modify_original(
        self,
    ) -> None:
        state = make_river_state()

        root = build_game_tree(state)

        self.assertIsNot(
            root.state,
            state,
        )
        self.assertEqual(
            state.pot,
            100,
        )
        self.assertEqual(
            state.players[0].stack,
            100,
        )
        self.assertEqual(
            state.players[1].stack,
            100,
        )
        self.assertEqual(
            state.action_history,
            [],
        )
        self.assertFalse(state.terminal)

    def test_root_has_three_children(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        self.assertEqual(
            len(root.children),
            3,
        )

        actions = [child.action_from_parent for child in root.children]

        self.assertEqual(
            actions,
            [
                Action(ActionType.CHECK),
                Action(
                    ActionType.BET,
                    amount=50,
                ),
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ),
            ],
        )

    def test_expected_node_counts(
        self,
    ) -> None:
        """
        現在のゲーム木:

        root
        ├─ check
        │  ├─ check
        │  ├─ bet50
        │  │  ├─ fold
        │  │  └─ call
        │  └─ all-in100
        │     ├─ fold
        │     └─ call
        ├─ bet50
        │  ├─ fold
        │  └─ call
        └─ all-in100
           ├─ fold
           └─ call

        内訳:

        root                    1

        check以下:
            check               1
            check-check         1
            bet                 1
            bet-fold            1
            bet-call            1
            all-in              1
            all-in-fold         1
            all-in-call         1

        bet以下:
            bet                 1
            bet-fold            1
            bet-call            1

        all-in以下:
            all-in              1
            all-in-fold         1
            all-in-call         1

        全ノード数:
            1 + 8 + 3 + 3 = 15

        終端ノード数:
            check以下5
            bet以下2
            all-in以下2
            合計9
        """

        root = build_game_tree(make_river_state())

        self.assertEqual(
            count_nodes(root),
            15,
        )
        self.assertEqual(
            count_terminal_nodes(root),
            9,
        )
        self.assertEqual(
            count_leaf_nodes(root),
            9,
        )

    def test_all_leaf_nodes_are_terminal(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        leaves = list(iter_leaf_nodes(root))

        self.assertEqual(
            len(leaves),
            9,
        )

        for leaf in leaves:
            self.assertTrue(leaf.is_terminal)

    def test_all_terminal_nodes_are_leaves(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        terminals = list(iter_terminal_nodes(root))

        self.assertEqual(
            len(terminals),
            9,
        )

        for terminal in terminals:
            self.assertTrue(terminal.is_leaf)

    def test_iter_nodes_contains_root_first(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        nodes = list(iter_nodes(root))

        self.assertEqual(
            len(nodes),
            15,
        )
        self.assertIs(
            nodes[0],
            root,
        )

    def test_maximum_depth(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        # 最長経路:
        # check -> bet/all-in -> fold/call
        self.assertEqual(
            max_depth(root),
            3,
        )

    def test_terminal_root_creates_single_node(
        self,
    ) -> None:
        state = make_river_state()

        state.apply_action(Action(ActionType.CHECK))
        state.apply_action(Action(ActionType.CHECK))

        root = build_game_tree(state)

        self.assertTrue(root.is_terminal)
        self.assertTrue(root.is_leaf)
        self.assertEqual(
            root.children,
            [],
        )
        self.assertEqual(
            count_nodes(root),
            1,
        )
        self.assertEqual(
            count_terminal_nodes(root),
            1,
        )
        self.assertEqual(
            count_leaf_nodes(root),
            1,
        )
        self.assertEqual(
            max_depth(root),
            0,
        )


class TestActionPaths(unittest.TestCase):
    def test_expected_number_of_paths(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertEqual(
            len(paths),
            9,
        )

    def test_paths_include_check_check(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(ActionType.CHECK),
                Action(ActionType.CHECK),
            ),
            paths,
        )

    def test_paths_include_check_bet_fold(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(ActionType.CHECK),
                Action(
                    ActionType.BET,
                    amount=50,
                ),
                Action(ActionType.FOLD),
            ),
            paths,
        )

    def test_paths_include_check_bet_call(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(ActionType.CHECK),
                Action(
                    ActionType.BET,
                    amount=50,
                ),
                Action(
                    ActionType.CALL,
                    amount=50,
                ),
            ),
            paths,
        )

    def test_paths_include_check_all_in_fold(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(ActionType.CHECK),
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ),
                Action(ActionType.FOLD),
            ),
            paths,
        )

    def test_paths_include_check_all_in_call(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(ActionType.CHECK),
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ),
                Action(
                    ActionType.CALL,
                    amount=100,
                ),
            ),
            paths,
        )

    def test_paths_include_bet_fold(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(
                    ActionType.BET,
                    amount=50,
                ),
                Action(ActionType.FOLD),
            ),
            paths,
        )

    def test_paths_include_bet_call(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(
                    ActionType.BET,
                    amount=50,
                ),
                Action(
                    ActionType.CALL,
                    amount=50,
                ),
            ),
            paths,
        )

    def test_paths_include_all_in_fold(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ),
                Action(ActionType.FOLD),
            ),
            paths,
        )

    def test_paths_include_all_in_call(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)

        self.assertIn(
            (
                Action(
                    ActionType.ALL_IN,
                    amount=100,
                ),
                Action(
                    ActionType.CALL,
                    amount=100,
                ),
            ),
            paths,
        )

    def test_all_paths_end_at_terminal_states(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        paths = action_paths(root)
        terminal_nodes = list(iter_terminal_nodes(root))

        self.assertEqual(
            len(paths),
            len(terminal_nodes),
        )
        self.assertEqual(
            len(paths),
            9,
        )

    def test_format_action_path(
        self,
    ) -> None:
        path = (
            Action(ActionType.CHECK),
            Action(
                ActionType.BET,
                amount=50,
            ),
            Action(
                ActionType.CALL,
                amount=50,
            ),
        )

        self.assertEqual(
            format_action_path(path),
            "check -> bet(50) -> call(50)",
        )

    def test_format_game_tree(
        self,
    ) -> None:
        root = build_game_tree(make_river_state())

        output = format_game_tree(root)

        self.assertIn(
            "ROOT",
            output,
        )
        self.assertIn(
            "check",
            output,
        )
        self.assertIn(
            "bet(50)",
            output,
        )
        self.assertIn(
            "all_in(100)",
            output,
        )
        self.assertIn(
            "fold",
            output,
        )
        self.assertIn(
            "call(50)",
            output,
        )
        self.assertIn(
            "call(100)",
            output,
        )
        self.assertIn(
            "terminal",
            output,
        )
        self.assertIn(
            "showdown",
            output,
        )
        self.assertIn(
            "winner=P0",
            output,
        )
        self.assertIn(
            "winner=P1",
            output,
        )


if __name__ == "__main__":
    unittest.main()
