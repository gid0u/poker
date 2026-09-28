import pytest

from poker_evaluator.cards import parse_card
from poker_evaluator.showdown import (
    ShowdownResult,
    compare_holdem,
)


def test_player1_wins_with_higher_pair() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    player2_hole = [
        parse_card("Ks"),
        parse_card("Kh"),
    ]

    board_cards = [
        parse_card("2c"),
        parse_card("7d"),
        parse_card("9s"),
        parse_card("Jc"),
        parse_card("Qh"),
    ]

    result = compare_holdem(
        player1_hole,
        player2_hole,
        board_cards,
    )

    assert result is ShowdownResult.PLAYER1_WIN


def test_player2_wins_with_one_pair() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Kd"),
    ]

    player2_hole = [
        parse_card("Qs"),
        parse_card("Qh"),
    ]

    board_cards = [
        parse_card("2c"),
        parse_card("7d"),
        parse_card("9s"),
        parse_card("Jc"),
        parse_card("3h"),
    ]

    result = compare_holdem(
        player1_hole,
        player2_hole,
        board_cards,
    )

    assert result is ShowdownResult.PLAYER2_WIN


def test_players_tie_when_playing_the_board() -> None:
    player1_hole = [
        parse_card("2c"),
        parse_card("3d"),
    ]

    player2_hole = [
        parse_card("4h"),
        parse_card("5c"),
    ]

    board_cards = [
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    result = compare_holdem(
        player1_hole,
        player2_hole,
        board_cards,
    )

    assert result is ShowdownResult.TIE


def test_showdown_rejects_duplicate_cards_between_players() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    player2_hole = [
        parse_card("As"),
        parse_card("Kh"),
    ]

    board_cards = [
        parse_card("2c"),
        parse_card("7d"),
        parse_card("9s"),
        parse_card("Jc"),
        parse_card("Qh"),
    ]

    with pytest.raises(ValueError):
        compare_holdem(
            player1_hole,
            player2_hole,
            board_cards,
        )
