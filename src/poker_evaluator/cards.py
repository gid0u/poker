from dataclasses import dataclass


RANKS: dict[str, int] = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "T": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
}

SUITS: dict[str, int] = {
    "s": 0,
    "c": 1,
    "h": 2,
    "d": 3,
}


@dataclass(frozen=True, order=True)
class Card:
    """トランプのカード1枚を表すクラス。"""

    rank: int
    suit: int

    def __post_init__(self) -> None:
        if self.rank not in RANKS.values():
            raise ValueError(f"不正なランクです: {self.rank}")

        if self.suit not in SUITS.values():
            raise ValueError(f"不正なスートです: {self.suit}")


def parse_card(text: str) -> Card:
    """'As'や'3h'のような文字列をCardへ変換する。"""

    text = text.strip()

    if len(text) != 2:
        raise ValueError(
            f"カード表記はランクとスートの2文字で入力してください: {text!r}"
        )

    rank_text = text[0].upper()
    suit_text = text[1].lower()

    if rank_text not in RANKS:
        raise ValueError(f"不正なランクです: {rank_text!r}")

    if suit_text not in SUITS:
        raise ValueError(f"不正なスートです: {suit_text!r}")

    return Card(
        rank=RANKS[rank_text],
        suit=SUITS[suit_text],
    )


def create_deck() -> tuple[Card, ...]:
    """重複のない標準52枚デッキを生成する。"""

    return tuple(
        Card(rank=rank, suit=suit) for rank in RANKS.values() for suit in SUITS.values()
    )
