import pytest

from poker_evaluator.cards import parse_card
from poker_evaluator.holdem import evaluate_holdem


def test_holdem_can_play_the_board() -> None:
    hole_cards = [
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

    value, rank, best_hands = evaluate_holdem(
        hole_cards,
        board_cards,
    )

    assert value == (8, 14)
    assert rank == 1
    assert len(best_hands) == 1
    assert set(best_hands[0]) == set(board_cards)


def test_holdem_can_use_both_hole_cards() -> None:
    hole_cards = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    board_cards = [
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("Ks"),
        parse_card("2c"),
        parse_card("3d"),
    ]

    value, rank, _ = evaluate_holdem(
        hole_cards,
        board_cards,
    )

    assert value == (6, 14, 13)
    assert rank > 1


def test_holdem_rejects_wrong_hole_card_count() -> None:
    hole_cards = [
        parse_card("As"),
    ]

    board_cards = [
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("Ks"),
        parse_card("2c"),
        parse_card("3d"),
    ]

    with pytest.raises(ValueError):
        evaluate_holdem(hole_cards, board_cards)


def test_holdem_rejects_duplicate_cards() -> None:
    hole_cards = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    board_cards = [
        parse_card("As"),
        parse_card("Kd"),
        parse_card("Ks"),
        parse_card("2c"),
        parse_card("3d"),
    ]

    with pytest.raises(ValueError):
        evaluate_holdem(hole_cards, board_cards)
