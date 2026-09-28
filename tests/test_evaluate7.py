import pytest

from poker_evaluator.cards import parse_card

from itertools import permutations

from poker_evaluator.evaluate7 import (
    best_five_hands,
    evaluate7,
    validate_seven_cards,
)


def test_evaluate7_can_use_board_only() -> None:
    cards = [
        parse_card("2c"),
        parse_card("3d"),
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    assert evaluate7(cards) == (8, 14)


def test_evaluate7_can_use_one_hole_card() -> None:
    cards = [
        parse_card("As"),
        parse_card("2c"),
        parse_card("Kh"),
        parse_card("Qd"),
        parse_card("Jc"),
        parse_card("Ts"),
        parse_card("3h"),
    ]

    assert evaluate7(cards) == (4, 14)


def test_evaluate7_can_use_two_hole_cards() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Ad"),
        parse_card("2s"),
        parse_card("3h"),
        parse_card("4c"),
    ]

    assert evaluate7(cards) == (7, 14, 4)


def test_validate_seven_cards_rejects_six_cards() -> None:
    cards = [
        parse_card("As"),
        parse_card("Kh"),
        parse_card("Qc"),
        parse_card("Jd"),
        parse_card("Ts"),
        parse_card("9h"),
    ]

    with pytest.raises(ValueError):
        validate_seven_cards(cards)


def test_validate_seven_cards_rejects_duplicate_card() -> None:
    cards = [
        parse_card("As"),
        parse_card("As"),
        parse_card("Qc"),
        parse_card("Jd"),
        parse_card("Ts"),
        parse_card("9h"),
        parse_card("8c"),
    ]

    with pytest.raises(ValueError):
        validate_seven_cards(cards)


def test_best_five_hands_returns_board_royal_flush() -> None:
    cards = [
        parse_card("2c"),
        parse_card("3d"),
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    value, best_hands = best_five_hands(cards)

    expected_cards = {
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    }

    assert value == (8, 14)
    assert len(best_hands) == 1
    assert set(best_hands[0]) == expected_cards


def test_best_five_hands_can_have_multiple_equivalent_subsets() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ks"),
        parse_card("Kh"),
        parse_card("Qs"),
        parse_card("Qh"),
        parse_card("2c"),
    ]

    value, best_hands = best_five_hands(cards)

    assert value == (2, 14, 13, 12)
    assert len(best_hands) == 2


def test_evaluate7_matches_best_five_value() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ks"),
        parse_card("Kh"),
        parse_card("Qs"),
        parse_card("Qh"),
        parse_card("2c"),
    ]

    value = evaluate7(cards)
    best_value, _ = best_five_hands(cards)

    assert value == best_value


def test_evaluate7_selects_best_full_house() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Ks"),
        parse_card("Kh"),
        parse_card("Kc"),
        parse_card("2d"),
    ]

    assert evaluate7(cards) == (6, 14, 13)


def test_evaluate7_is_independent_of_card_order() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("Ks"),
        parse_card("2c"),
        parse_card("3h"),
    ]

    expected = (6, 14, 13)

    for ordered_cards in permutations(cards):
        assert evaluate7(list(ordered_cards)) == expected
