from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from random import Random
from typing import Iterable, Iterator

from .cards import Card


RANKS: tuple[int, ...] = tuple(range(2, 15))
SUITS: tuple[int, ...] = (0, 1, 2, 3)


def full_deck_cards() -> tuple[Card, ...]:
    """
    標準52枚デッキを生成する。

    rank:
        2～14
        11=J, 12=Q, 13=K, 14=A

    suit:
        0=spades
        1=clubs
        2=hearts
        3=diamonds
    """

    return tuple(Card(rank=rank, suit=suit) for rank in RANKS for suit in SUITS)


@dataclass
class Deck:
    """
    テキサスホールデム用の52枚デッキ。
    """

    cards: list[Card]

    @classmethod
    def create(cls) -> "Deck":
        return cls(cards=list(full_deck_cards()))

    @classmethod
    def from_cards(
        cls,
        cards: Iterable[Card],
    ) -> "Deck":
        card_list = list(cards)

        if len(card_list) != len(set(card_list)):
            raise ValueError("Deck cannot contain duplicate cards.")

        return cls(cards=card_list)

    def clone(self) -> "Deck":
        return Deck(cards=list(self.cards))

    def __len__(self) -> int:
        return len(self.cards)

    def __iter__(self) -> Iterator[Card]:
        return iter(self.cards)

    def __contains__(
        self,
        card: Card,
    ) -> bool:
        return card in self.cards

    def remove(
        self,
        card: Card,
    ) -> None:
        try:
            self.cards.remove(card)
        except ValueError as exc:
            raise ValueError(f"Card is not available in deck: {card}") from exc

    def remove_many(
        self,
        cards: Iterable[Card],
    ) -> None:
        card_tuple = tuple(cards)

        if len(card_tuple) != len(set(card_tuple)):
            raise ValueError("Cannot remove duplicate cards.")

        missing_cards = [card for card in card_tuple if card not in self.cards]

        if missing_cards:
            raise ValueError(f"Some cards are not available in deck: {missing_cards}")

        for card in card_tuple:
            self.cards.remove(card)

    def shuffled(
        self,
        seed: int | None = None,
    ) -> "Deck":
        copied_cards = list(self.cards)

        random_generator = Random(seed)
        random_generator.shuffle(copied_cards)

        return Deck(cards=copied_cards)

    def shuffle(
        self,
        seed: int | None = None,
    ) -> None:
        random_generator = Random(seed)
        random_generator.shuffle(self.cards)

    def draw(
        self,
        count: int = 1,
    ) -> tuple[Card, ...]:
        if count < 0:
            raise ValueError("Draw count must not be negative.")

        if count > len(self.cards):
            raise ValueError("Cannot draw more cards than remain in the deck.")

        drawn = tuple(self.cards[:count])

        del self.cards[:count]

        return drawn

    def sample(
        self,
        count: int,
        seed: int | None = None,
    ) -> tuple[Card, ...]:
        if count < 0:
            raise ValueError("Sample count must not be negative.")

        if count > len(self.cards):
            raise ValueError("Cannot sample more cards than remain in the deck.")

        random_generator = Random(seed)

        return tuple(
            random_generator.sample(
                self.cards,
                count,
            )
        )

    def combinations(
        self,
        count: int,
    ) -> Iterator[tuple[Card, ...]]:
        if count < 0:
            raise ValueError("Combination count must not be negative.")

        if count > len(self.cards):
            return iter(())

        return combinations(
            self.cards,
            count,
        )

    def hole_card_combinations(
        self,
    ) -> Iterator[tuple[Card, Card]]:
        for first, second in combinations(
            self.cards,
            2,
        ):
            yield first, second
