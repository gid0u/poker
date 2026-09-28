import pytest

from poker_evaluator.cards import parse_card
from poker_evaluator.equity import calculate_multiway_exact_equity


def test_three_way_exact_equity_from_turn() -> None:
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
    ]

    result = calculate_multiway_exact_equity(
        player_holes,
        board_cards,
    )

    assert result.total == 42
    assert result.outright_wins == (38, 2, 2)
    assert result.tie_participations == (0, 0, 0)

    assert result.equities == pytest.approx(
        (
            38 / 42,
            2 / 42,
            2 / 42,
        )
    )

    assert sum(result.equities) == pytest.approx(1.0)


def test_three_way_tie_splits_pot_into_thirds() -> None:
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

    result = calculate_multiway_exact_equity(
        player_holes,
        board_cards,
    )

    assert result.total == 1
    assert result.outright_wins == (0, 0, 0)
    assert result.tie_participations == (1, 1, 1)
    assert result.share_totals == pytest.approx(
        (
            1 / 3,
            1 / 3,
            1 / 3,
        )
    )
    assert result.equities == pytest.approx(
        (
            1 / 3,
            1 / 3,
            1 / 3,
        )
    )


def test_two_players_can_split_pot_while_third_loses() -> None:
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

    result = calculate_multiway_exact_equity(
        player_holes,
        board_cards,
    )

    assert result.total == 1
    assert result.outright_wins == (0, 0, 0)
    assert result.tie_participations == (1, 1, 0)
    assert result.equities == pytest.approx(
        (
            0.5,
            0.5,
            0.0,
        )
    )


def test_multiway_exact_equity_rejects_preflop_board() -> None:
    player_holes = [
        [parse_card("As"), parse_card("Ah")],
        [parse_card("Ks"), parse_card("Kh")],
        [parse_card("Qs"), parse_card("Qh")],
    ]

    with pytest.raises(ValueError):
        calculate_multiway_exact_equity(
            player_holes,
            board_cards=[],
        )
