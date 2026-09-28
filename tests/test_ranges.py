import pytest

from poker_evaluator.cards import parse_card
from poker_evaluator.ranges import (
    expand_range_token,
    filter_blocked_combos,
    parse_range,
)


def test_pocket_aces_has_six_combinations() -> None:
    combos = expand_range_token("AA")

    assert len(combos) == 6

    for card1, card2 in combos:
        assert card1.rank == 14
        assert card2.rank == 14
        assert card1.suit != card2.suit


def test_aks_has_four_suited_combinations() -> None:
    combos = expand_range_token("AKs")

    assert len(combos) == 4

    for card1, card2 in combos:
        assert {card1.rank, card2.rank} == {14, 13}
        assert card1.suit == card2.suit


def test_ako_has_twelve_offsuit_combinations() -> None:
    combos = expand_range_token("AKo")

    assert len(combos) == 12

    for card1, card2 in combos:
        assert {card1.rank, card2.rank} == {14, 13}
        assert card1.suit != card2.suit


def test_ak_without_suffix_has_sixteen_combinations() -> None:
    combos = expand_range_token("AK")

    assert len(combos) == 16


def test_tt_plus_has_thirty_combinations() -> None:
    combos = expand_range_token("TT+")

    assert len(combos) == 30

    pair_ranks = {card1.rank for card1, card2 in combos if card1.rank == card2.rank}

    assert pair_ranks == {10, 11, 12, 13, 14}


def test_parse_range_combines_multiple_tokens() -> None:
    combos = parse_range("AA, AKs")

    assert len(combos) == 10


def test_known_ace_blocks_three_aa_combinations() -> None:
    combos = expand_range_token("AA")

    available = filter_blocked_combos(
        combos,
        known_cards=[parse_card("As")],
    )

    assert len(available) == 3

    for combo in available:
        assert parse_card("As") not in combo


def test_pair_cannot_have_suited_suffix() -> None:
    with pytest.raises(ValueError):
        expand_range_token("AAs")


def test_non_pair_plus_is_not_yet_supported() -> None:
    with pytest.raises(ValueError):
        expand_range_token("AJs+")
