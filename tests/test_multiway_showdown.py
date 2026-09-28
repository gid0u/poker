import pytest

from poker_evaluator.cards import parse_card
from poker_evaluator.showdown import compare_multiway_holdem


def test_player1_wins_three_way_showdown() -> None:
    player_holes = [
        [parse_card("As"), parse_card("Ah")],
        [parse_card("Ks"), parse_card("Kh")],
        [parse_card("Qs"), parse_card("Qh")],
    ]

    board_cards = [
        parse_card("2c"),
        parse_card("7d"),
        parse_card("9s"),
        parse_card("Jc"),
        parse_card("3h"),
    ]

    result = compare_multiway_holdem(
        player_holes,
        board_cards,
    )

    assert result.winner_indices == (0,)
    assert result.is_tie is False


def test_two_players_can_tie_while_third_player_loses() -> None:
    player_holes = [
        [parse_card("Ts"), parse_card("3d")],
        [parse_card("Th"), parse_card("4d")],
        [parse_card("9c"), parse_card("9d")],
    ]

    board_cards = [
        parse_card("As"),
        parse_card("Kd"),
        parse_card("Qs"),
        parse_card("Jc"),
        parse_card("2h"),
    ]

    result = compare_multiway_holdem(
        player_holes,
        board_cards,
    )

    assert result.winner_indices == (0, 1)
    assert result.is_tie is True


def test_all_players_can_play_the_board() -> None:
    player_holes = [
        [parse_card("2c"), parse_card("3d")],
        [parse_card("4h"), parse_card("5c")],
        [parse_card("6d"), parse_card("7h")],
    ]

    board_cards = [
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    result = compare_multiway_holdem(
        player_holes,
        board_cards,
    )

    assert result.winner_indices == (0, 1, 2)
    assert result.is_tie is True
    assert result.hand_values == (
        (8, 14),
        (8, 14),
        (8, 14),
    )


def test_multiway_showdown_rejects_one_player() -> None:
    player_holes = [
        [parse_card("As"), parse_card("Ah")],
    ]

    board_cards = [
        parse_card("2c"),
        parse_card("7d"),
        parse_card("9s"),
        parse_card("Jc"),
        parse_card("3h"),
    ]

    with pytest.raises(ValueError):
        compare_multiway_holdem(
            player_holes,
            board_cards,
        )


def test_multiway_showdown_rejects_duplicate_cards() -> None:
    player_holes = [
        [parse_card("As"), parse_card("Ah")],
        [parse_card("As"), parse_card("Kh")],
        [parse_card("Qs"), parse_card("Qh")],
    ]

    board_cards = [
        parse_card("2c"),
        parse_card("7d"),
        parse_card("9s"),
        parse_card("Jc"),
        parse_card("3h"),
    ]

    with pytest.raises(ValueError):
        compare_multiway_holdem(
            player_holes,
            board_cards,
        )
