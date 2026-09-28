from itertools import permutations

import pytest


from poker_evaluator.evaluate5 import (
    count_ranks,
    straight_high,
    validate_five_cards,
)

from poker_evaluator.evaluate5 import (
    count_ranks,
    is_flush,
    straight_high,
    validate_five_cards,
)

from poker_evaluator.cards import Card, parse_card
from poker_evaluator.evaluate5 import straight_high, validate_five_cards

from poker_evaluator.evaluate5 import (
    count_ranks,
    is_flush,
    rank_groups,
    straight_high,
    validate_five_cards,
)

from poker_evaluator.evaluate5 import (
    count_ranks,
    evaluate5,
    is_flush,
    rank_groups,
    straight_high,
    validate_five_cards,
)


def test_ace_high_straight() -> None:
    assert straight_high([14, 13, 12, 11, 10]) == 14


def test_six_high_straight() -> None:
    assert straight_high([6, 5, 4, 3, 2]) == 6


def test_wheel_straight() -> None:
    assert straight_high([14, 5, 4, 3, 2]) == 5


def test_non_straight() -> None:
    assert straight_high([14, 13, 12, 11, 7]) is None


def test_duplicate_rank_is_not_straight() -> None:
    assert straight_high([5, 5, 4, 3, 2]) is None


def test_validate_five_cards_accepts_valid_hand() -> None:
    cards = [
        parse_card("As"),
        parse_card("Kh"),
        parse_card("Qc"),
        parse_card("Jd"),
        parse_card("Ts"),
    ]

    validate_five_cards(cards)


def test_validate_five_cards_rejects_four_cards() -> None:
    cards = [
        parse_card("As"),
        parse_card("Kh"),
        parse_card("Qc"),
        parse_card("Jd"),
    ]

    with pytest.raises(ValueError):
        validate_five_cards(cards)


def test_validate_five_cards_rejects_duplicate_card() -> None:
    cards = [
        parse_card("As"),
        parse_card("As"),
        parse_card("Qc"),
        parse_card("Jd"),
        parse_card("Ts"),
    ]

    with pytest.raises(ValueError):
        validate_five_cards(cards)


def test_count_ranks_for_one_pair() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Kc"),
        parse_card("Qd"),
        parse_card("Js"),
    ]

    counts = count_ranks(cards)

    assert counts[14] == 2
    assert counts[13] == 1
    assert counts[12] == 1
    assert counts[11] == 1


def test_count_ranks_for_full_house() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("Ks"),
    ]

    counts = count_ranks(cards)

    assert counts[14] == 3
    assert counts[13] == 2


def test_is_flush_returns_true_for_same_suit() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("9s"),
    ]

    assert is_flush(cards) is True


def test_is_flush_returns_false_for_mixed_suits() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("9h"),
    ]

    assert is_flush(cards) is False


def test_rank_groups_for_full_house() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("Ks"),
    ]

    assert rank_groups(cards) == [
        (3, 14),
        (2, 13),
    ]


def test_rank_groups_for_two_pair() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Kc"),
        parse_card("Kd"),
        parse_card("Qs"),
    ]

    assert rank_groups(cards) == [
        (2, 14),
        (2, 13),
        (1, 12),
    ]


def test_evaluate_royal_flush() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    assert evaluate5(cards) == (8, 14)


def test_evaluate_four_of_a_kind() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Ad"),
        parse_card("Ks"),
    ]

    assert evaluate5(cards) == (7, 14, 13)


def test_evaluate_full_house() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("Ks"),
    ]

    assert evaluate5(cards) == (6, 14, 13)


def test_evaluate_flush() -> None:
    cards = [
        parse_card("As"),
        parse_card("Js"),
        parse_card("8s"),
        parse_card("5s"),
        parse_card("2s"),
    ]

    assert evaluate5(cards) == (5, 14, 11, 8, 5, 2)


def test_evaluate_straight() -> None:
    cards = [
        parse_card("9s"),
        parse_card("8h"),
        parse_card("7c"),
        parse_card("6d"),
        parse_card("5s"),
    ]

    assert evaluate5(cards) == (4, 9)


def test_evaluate_three_of_a_kind() -> None:
    cards = [
        parse_card("Qs"),
        parse_card("Qh"),
        parse_card("Qc"),
        parse_card("Ad"),
        parse_card("Ks"),
    ]

    assert evaluate5(cards) == (3, 12, 14, 13)


def test_evaluate_two_pair() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Kc"),
        parse_card("Kd"),
        parse_card("Qs"),
    ]

    assert evaluate5(cards) == (2, 14, 13, 12)


def test_evaluate_one_pair() -> None:
    cards = [
        parse_card("Js"),
        parse_card("Jh"),
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("9s"),
    ]

    assert evaluate5(cards) == (1, 11, 14, 13, 9)


def test_evaluate_high_card() -> None:
    cards = [
        parse_card("As"),
        parse_card("Kh"),
        parse_card("Qc"),
        parse_card("Jd"),
        parse_card("7s"),
    ]

    assert evaluate5(cards) == (0, 14, 13, 12, 11, 7)


def test_evaluate_wheel_straight() -> None:
    cards = [
        parse_card("As"),
        parse_card("2h"),
        parse_card("3c"),
        parse_card("4d"),
        parse_card("5s"),
    ]

    assert evaluate5(cards) == (4, 5)


def test_evaluate_wheel_straight_flush() -> None:
    cards = [
        parse_card("As"),
        parse_card("2s"),
        parse_card("3s"),
        parse_card("4s"),
        parse_card("5s"),
    ]

    assert evaluate5(cards) == (8, 5)


def test_six_high_straight_beats_wheel_straight() -> None:
    wheel = [
        parse_card("As"),
        parse_card("2h"),
        parse_card("3c"),
        parse_card("4d"),
        parse_card("5s"),
    ]

    six_high = [
        parse_card("6s"),
        parse_card("5h"),
        parse_card("4c"),
        parse_card("3d"),
        parse_card("2s"),
    ]

    assert evaluate5(six_high) > evaluate5(wheel)


def test_higher_four_of_a_kind_wins() -> None:
    aces = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Ad"),
        parse_card("2s"),
    ]

    kings = [
        parse_card("Ks"),
        parse_card("Kh"),
        parse_card("Kc"),
        parse_card("Kd"),
        parse_card("As"),
    ]

    assert evaluate5(aces) > evaluate5(kings)


def test_full_house_compares_trips_first() -> None:
    aces_full = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("2d"),
        parse_card("2s"),
    ]

    kings_full = [
        parse_card("Ks"),
        parse_card("Kh"),
        parse_card("Kc"),
        parse_card("Ad"),
        parse_card("As"),
    ]

    assert evaluate5(aces_full) > evaluate5(kings_full)


def test_flush_compares_each_rank_in_order() -> None:
    jack_second = [
        parse_card("As"),
        parse_card("Js"),
        parse_card("8s"),
        parse_card("5s"),
        parse_card("2s"),
    ]

    ten_second = [
        parse_card("Ah"),
        parse_card("Th"),
        parse_card("9h"),
        parse_card("7h"),
        parse_card("3h"),
    ]

    assert evaluate5(jack_second) > evaluate5(ten_second)


def test_two_pair_compares_lower_pair_after_higher_pair() -> None:
    aces_and_kings = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Kc"),
        parse_card("Kd"),
        parse_card("Qs"),
    ]

    aces_and_queens = [
        parse_card("Ac"),
        parse_card("Ad"),
        parse_card("Qc"),
        parse_card("Qd"),
        parse_card("Ks"),
    ]

    assert evaluate5(aces_and_kings) > evaluate5(aces_and_queens)


def test_one_pair_compares_kickers_in_order() -> None:
    king_kicker = [
        parse_card("Js"),
        parse_card("Jh"),
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("9s"),
    ]

    queen_kicker = [
        parse_card("Jc"),
        parse_card("Jd"),
        parse_card("Ah"),
        parse_card("Qc"),
        parse_card("Ts"),
    ]

    assert evaluate5(king_kicker) > evaluate5(queen_kicker)


def test_evaluate5_is_independent_of_card_order() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ah"),
        parse_card("Ac"),
        parse_card("Kd"),
        parse_card("Ks"),
    ]

    expected = (6, 14, 13)

    for ordered_cards in permutations(cards):
        assert evaluate5(list(ordered_cards)) == expected


def test_evaluate5_is_independent_of_suit_names() -> None:
    cards = [
        parse_card("As"),
        parse_card("Ks"),
        parse_card("Qs"),
        parse_card("Js"),
        parse_card("Ts"),
    ]

    suit_mapping = {
        0: 2,
        1: 3,
        2: 1,
        3: 0,
    }

    renamed_cards = [
        Card(
            rank=card.rank,
            suit=suit_mapping[card.suit],
        )
        for card in cards
    ]

    assert evaluate5(renamed_cards) == evaluate5(cards)
