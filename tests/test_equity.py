import pytest

from poker_evaluator.equity import (
    calculate_exact_equity,
    calculate_monte_carlo_equity,
)

from poker_evaluator.cards import parse_card
from poker_evaluator.equity import calculate_exact_equity


def test_exact_equity_from_flop_with_locked_royal_flush() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Ks"),
    ]

    player2_hole = [
        parse_card("2c"),
        parse_card("2d"),
    ]

    board_cards = [
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    result = calculate_exact_equity(
        player1_hole,
        player2_hole,
        board_cards,
    )

    assert result.total == 990
    assert result.player1_wins == 990
    assert result.player2_wins == 0
    assert result.ties == 0
    assert result.player1_equity == 1.0
    assert result.player2_equity == 0.0


def test_exact_equity_from_turn_has_44_possible_rivers() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Ks"),
    ]

    player2_hole = [
        parse_card("2c"),
        parse_card("2d"),
    ]

    board_cards = [
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
        parse_card("3h"),
    ]

    result = calculate_exact_equity(
        player1_hole,
        player2_hole,
        board_cards,
    )

    assert result.total == 44
    assert result.player1_wins == 44
    assert result.player2_wins == 0
    assert result.ties == 0


def test_exact_equity_on_complete_board_can_tie() -> None:
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

    result = calculate_exact_equity(
        player1_hole,
        player2_hole,
        board_cards,
    )

    assert result.total == 1
    assert result.player1_wins == 0
    assert result.player2_wins == 0
    assert result.ties == 1
    assert result.player1_equity == 0.5
    assert result.player2_equity == 0.5


def test_exact_equity_rejects_preflop_board() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    player2_hole = [
        parse_card("Ks"),
        parse_card("Kh"),
    ]

    with pytest.raises(ValueError):
        calculate_exact_equity(
            player1_hole,
            player2_hole,
            [],
        )


def test_exact_equity_rejects_duplicate_known_cards() -> None:
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
    ]

    with pytest.raises(ValueError):
        calculate_exact_equity(
            player1_hole,
            player2_hole,
            board_cards,
        )


def test_monte_carlo_equity_runs_preflop_simulation() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    player2_hole = [
        parse_card("Ks"),
        parse_card("Kh"),
    ]

    result = calculate_monte_carlo_equity(
        player1_hole,
        player2_hole,
        board_cards=[],
        iterations=500,
        seed=12345,
    )

    assert result.total == 500
    assert result.player1_wins + result.player2_wins + result.ties == 500
    assert result.player1_equity + result.player2_equity == pytest.approx(1.0)


def test_monte_carlo_equity_is_reproducible_with_same_seed() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Kd"),
    ]

    player2_hole = [
        parse_card("Qs"),
        parse_card("Qh"),
    ]

    first = calculate_monte_carlo_equity(
        player1_hole,
        player2_hole,
        board_cards=[],
        iterations=200,
        seed=2026,
    )

    second = calculate_monte_carlo_equity(
        player1_hole,
        player2_hole,
        board_cards=[],
        iterations=200,
        seed=2026,
    )

    assert first == second


def test_monte_carlo_equity_on_locked_tie() -> None:
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

    result = calculate_monte_carlo_equity(
        player1_hole,
        player2_hole,
        board_cards,
        iterations=25,
        seed=1,
    )

    assert result.player1_wins == 0
    assert result.player2_wins == 0
    assert result.ties == 25
    assert result.player1_equity == 0.5
    assert result.player2_equity == 0.5


def test_monte_carlo_equity_rejects_zero_iterations() -> None:
    with pytest.raises(ValueError):
        calculate_monte_carlo_equity(
            [parse_card("As"), parse_card("Ah")],
            [parse_card("Ks"), parse_card("Kh")],
            board_cards=[],
            iterations=0,
        )
