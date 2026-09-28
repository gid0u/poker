import pytest

from poker_evaluator.cards import Card, create_deck, parse_card
from poker_evaluator.evaluate5 import straight_high, validate_five_cards


def test_parse_ace_of_spades() -> None:
    assert parse_card("As") == Card(rank=14, suit=0)


def test_parse_king_of_hearts_case_insensitive() -> None:
    assert parse_card("kH") == Card(rank=13, suit=2)


def test_parse_card_ignores_outer_spaces() -> None:
    assert parse_card(" 3c ") == Card(rank=3, suit=1)


def test_invalid_rank_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_card("Xs")


def test_invalid_suit_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_card("Az")


def test_invalid_length_is_rejected() -> None:
    with pytest.raises(ValueError):
        parse_card("10s")


from poker_evaluator.cards import create_deck


def test_create_deck_has_52_cards() -> None:
    deck = create_deck()

    assert len(deck) == 52


def test_create_deck_has_no_duplicates() -> None:
    deck = create_deck()

    assert len(set(deck)) == 52


def test_create_deck_contains_ace_of_spades() -> None:
    deck = create_deck()

    assert Card(rank=14, suit=0) in deck


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
