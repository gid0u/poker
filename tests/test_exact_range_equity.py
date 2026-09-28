import pytest

from poker_evaluator.cards import parse_card
from poker_evaluator.equity import (
    calculate_hero_exact_equity_vs_range,
)


def test_exact_range_equity_on_turn() -> None:
    hero_hole = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    board_cards = [
        parse_card("2c"),
        parse_card("7d"),
        parse_card("9s"),
        parse_card("Jc"),
    ]

    result = calculate_hero_exact_equity_vs_range(
        hero_hole=hero_hole,
        opponent_range="KK",
        board_cards=board_cards,
    )

    # KKは6コンボ、各コンボについてリバー44通り
    assert result.total == 6 * 44

    # 各KKコンボについて、残り2枚のKだけが相手の勝ち
    assert result.outright_wins == 6 * 42
    assert result.losses == 6 * 2
    assert result.tie_participations == 0

    assert result.equity == pytest.approx(252 / 264)


def test_exact_range_equity_on_board_royal_flush() -> None:
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

    result = calculate_hero_exact_equity_vs_range(
        hero_hole=hero_hole,
        opponent_range="AA",
        board_cards=board_cards,
    )

    # Asがボードにあるので、相手のAAは残り3コンボ
    assert result.total == 3
    assert result.outright_wins == 0
    assert result.tie_participations == 3
    assert result.losses == 0
    assert result.share_total == pytest.approx(1.5)
    assert result.equity == pytest.approx(0.5)


def test_exact_range_equity_with_locked_royal_flush() -> None:
    hero_hole = [
        parse_card("As"),
        parse_card("Ks"),
    ]

    board_cards = [
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
        parse_card("2c"),
        parse_card("3d"),
    ]

    result = calculate_hero_exact_equity_vs_range(
        hero_hole=hero_hole,
        opponent_range="AA",
        board_cards=board_cards,
    )

    assert result.total == 3
    assert result.outright_wins == 3
    assert result.tie_participations == 0
    assert result.losses == 0
    assert result.equity == 1.0


def test_exact_range_equity_rejects_preflop() -> None:
    with pytest.raises(ValueError):
        calculate_hero_exact_equity_vs_range(
            hero_hole=[
                parse_card("As"),
                parse_card("Ah"),
            ],
            opponent_range="KK",
            board_cards=[],
        )
