import pytest

from poker_evaluator.rank_table import (
    load_rank_table,
    rank_from_value,
)

from poker_evaluator.cards import parse_card
from poker_evaluator.rank_table import (
    load_rank_table,
    rank_five_cards,
    rank_from_value,
    rank_seven_cards,
)


def test_rank_table_has_7462_classes() -> None:
    rank_table = load_rank_table()

    assert len(rank_table) == 7_462


def test_royal_flush_is_rank_one() -> None:
    assert rank_from_value((8, 14)) == 1


def test_weakest_high_card_is_rank_7462() -> None:
    assert rank_from_value((0, 7, 5, 4, 3, 2)) == 7_462


def test_akqj7_high_is_rank_6188() -> None:
    assert rank_from_value((0, 14, 13, 12, 11, 7)) == 6_188


def test_unknown_value_is_rejected() -> None:
    with pytest.raises(ValueError):
        rank_from_value((9, 14))


def test_rank_five_cards_for_royal_flush() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    assert rank_five_cards(cards) == 1


def test_rank_five_cards_for_akqj7_high() -> None:
    cards = [
        parse_card("As"),
        parse_card("Kh"),
        parse_card("Qc"),
        parse_card("Jd"),
        parse_card("7s"),
    ]

    assert rank_five_cards(cards) == 6_188


def test_rank_seven_cards_can_select_board_royal_flush() -> None:
    cards = [
        parse_card("2c"),
        parse_card("3d"),
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    assert rank_seven_cards(cards) == 1


def test_rank_seven_cards_matches_selected_full_house() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Ks"),
        parse_card("Kh"),
        parse_card("2c"),
        parse_card("3d"),
    ]

    assert rank_seven_cards(cards) == rank_from_value((6, 14, 13))
