import pytest

from poker_evaluator.cards import parse_card
from poker_evaluator.equity import calculate_hero_equity_vs_random


def test_hero_locked_royal_flush_always_wins() -> None:
    hero_hole = [
        parse_card("As"),
        parse_card("Ks"),
    ]

    board_cards = [
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    result = calculate_hero_equity_vs_random(
        hero_hole=hero_hole,
        opponent_count=2,
        board_cards=board_cards,
        iterations=100,
        seed=123,
    )

    assert result.total == 100
    assert result.outright_wins == 100
    assert result.tie_participations == 0
    assert result.losses == 0
    assert result.equity == 1.0


def test_board_royal_flush_splits_three_way_pot() -> None:
    hero_hole = [
        parse_card("2c"),
        parse_card("3d"),
    ]

    board_cards = [
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    result = calculate_hero_equity_vs_random(
        hero_hole=hero_hole,
        opponent_count=2,
        board_cards=board_cards,
        iterations=30,
        seed=456,
    )

    assert result.outright_wins == 0
    assert result.tie_participations == 30
    assert result.losses == 0
    assert result.share_total == pytest.approx(10.0)
    assert result.equity == pytest.approx(1 / 3)


def test_hero_equity_is_reproducible_with_same_seed() -> None:
    hero_hole = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    first = calculate_hero_equity_vs_random(
        hero_hole=hero_hole,
        opponent_count=3,
        board_cards=[],
        iterations=200,
        seed=2026,
    )

    second = calculate_hero_equity_vs_random(
        hero_hole=hero_hole,
        opponent_count=3,
        board_cards=[],
        iterations=200,
        seed=2026,
    )

    assert first == second

    assert first.outright_wins + first.tie_participations + first.losses == 200


def test_hero_equity_rejects_zero_opponents() -> None:
    with pytest.raises(ValueError):
        calculate_hero_equity_vs_random(
            hero_hole=[
                parse_card("As"),
                parse_card("Ah"),
            ],
            opponent_count=0,
            board_cards=[],
        )
