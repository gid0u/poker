"""Complete C(52,7) lookup: colex combinadic key -> existing 1..7462 rank.

Reader requires only the standard library. Generation is in seven_card_builder.
"""
from collections.abc import Mapping
from itertools import combinations
import hashlib
import json
from math import comb
import mmap
from pathlib import Path
import struct

from .cards import Card, parse_card

HAND_COUNT = comb(52, 7)
DATA_FILENAME = "seven_card_ranks.u16"
MANIFEST_FILENAME = "seven_card_ranks.json"
DEFAULT_DIRECTORY = Path(__file__).resolve().parents[2] / "data" / "processed" / "seven_card_dictionary"
CATEGORY_NAMES = ("high_card", "one_pair", "two_pair", "three_of_a_kind", "straight",
                  "flush", "full_house", "four_of_a_kind", "straight_flush")


def card_id(card):
    """Stable encoding: 4*(rank-2)+suit; suits s,c,h,d = 0,1,2,3."""
    if isinstance(card, str):
        card = parse_card(card)
    if isinstance(card, Card):
        return 4 * (card.rank - 2) + card.suit
    if type(card) is int and 0 <= card < 52:
        return card
    raise ValueError("Expected Card, card string or integer ID in [0,51]")


def hand_index(cards):
    if isinstance(cards, str):
        cards = cards.split()
    ids = sorted(card_id(c) for c in cards)
    if len(ids) != 7 or len(set(ids)) != 7:
        raise ValueError("Exactly seven distinct cards are required")
    return sum(comb(value, i) for i, value in enumerate(ids, 1))


def index_cards(index):
    if type(index) is not int or not 0 <= index < HAND_COUNT:
        raise ValueError("Index outside C(52,7)")
    ids = [0] * 7
    upper = 51
    for k in range(7, 0, -1):
        while comb(upper, k) > index:
            upper -= 1
        ids[k-1] = upper
        index -= comb(upper, k)
        upper -= 1
    return tuple(Card(i // 4 + 2, i % 4) for i in ids)


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class SevenCardRankDictionary(Mapping):
    """Read-only mapping from seven cards to a rank, with memory-mapped storage.

    `table['As Ks Qs Js Ts 2c 3d'] == 1`; use value() for the evaluator tuple.
    Close the mapping or use it as a context manager. Iterating all keys is costly.
    """
    def __init__(self, directory=DEFAULT_DIRECTORY, *, verify_checksum=False):
        self.directory = Path(directory)
        manifest = json.loads((self.directory / MANIFEST_FILENAME).read_text(encoding="utf-8"))
        if (manifest.get("format") != "poker-seven-card-colex-u16le-v1"
                or manifest.get("complete") is not True
                or manifest.get("hand_count") != HAND_COUNT
                or manifest.get("card_encoding") != "4*(rank-2)+suit; suits=s,c,h,d"
                or manifest.get("rank_order") != "1=strongest;7462=weakest"):
            raise ValueError("Unsupported or incomplete dictionary")
        self.values = tuple(tuple(v) for v in manifest["rank_values"])
        if len(self.values) != 7462 or self.values != tuple(sorted(set(self.values), reverse=True)):
            raise ValueError("Invalid rank classes")
        self.manifest = manifest
        path = self.directory / DATA_FILENAME
        if path.stat().st_size != HAND_COUNT * 2:
            raise ValueError("Dictionary file is truncated or has unexpected size")
        if verify_checksum and file_sha256(path) != manifest["sha256"]:
            raise ValueError("Dictionary checksum mismatch")
        self._file = path.open("rb")
        try:
            self._map = mmap.mmap(self._file.fileno(), 0, access=mmap.ACCESS_READ)
        except Exception:
            self._file.close()
            raise

    def __getitem__(self, cards):
        return self.rank_at(hand_index(cards))

    def rank_at(self, index):
        if type(index) is not int or not 0 <= index < HAND_COUNT:
            raise ValueError("Index outside C(52,7)")
        value = struct.unpack_from("<H", self._map, 2 * index)[0]
        if not 1 <= value <= 7462:
            raise ValueError("Corrupt or uninitialized rank")
        return value

    def value(self, cards):
        return self.values[self[cards] - 1]

    def category(self, cards):
        return CATEGORY_NAMES[self.value(cards)[0]]

    def evaluate_wildcards(self, pattern, **options):
        """Return the exact conditional mean/distribution, not the best completion."""
        from .wildcards import evaluate_wildcards
        return evaluate_wildcards(pattern, ranker=self, **options)

    def relative_strength(self, hero, board, opponent_ranges, **options):
        from .relative_strength import evaluate_relative_strength
        return evaluate_relative_strength(hero, board, opponent_ranges, ranker=self, **options)

    def relative_wildcards(self, pattern, opponent_ranges, **options):
        from .relative_strength import evaluate_relative_wildcards
        return evaluate_relative_wildcards(pattern, opponent_ranges, ranker=self, **options)

    @property
    def all_hands_statistics(self):
        """Registered baseline over all explicit hands, without wildcard expansion."""
        result = json.loads((self.directory / "all_hands_average.json").read_text(encoding="utf-8"))
        if (result.get("key") != "all_explicit_seven_card_hands"
                or result.get("hand_count") != HAND_COUNT
                or result.get("sha256") != self.manifest["sha256"]
                or result.get("wildcard_used") is not False):
            raise ValueError("Statistics do not match this dictionary")
        counts = {int(r): n for r, n in result["rank_counts"].items()}
        if (any(not 1 <= r <= 7462 or type(n) is not int or n <= 0 for r, n in counts.items())
                or sum(counts.values()) != HAND_COUNT
                or sum(r*n for r, n in counts.items()) != result["rank_sum"]
                or result["mean_rank"] != result["rank_sum"] / HAND_COUNT):
            raise ValueError("Inconsistent registered statistics")
        if result.get("schema_version", 1) >= 2:
            from fractions import Fraction
            square_sum = sum(r*r*n for r, n in counts.items())
            variance = Fraction(square_sum*HAND_COUNT-result["rank_sum"]**2, HAND_COUNT**2)
            if (result.get("rank_squared_sum") != square_sum
                    or result.get("variance_rank") != float(variance)):
                raise ValueError("Inconsistent registered variance")
        return result

    @property
    def all_hands_average_rank(self):
        return self.all_hands_statistics["mean_rank"]

    @property
    def all_hands_variance_rank(self):
        return self.all_hands_statistics["variance_rank"]

    @property
    def all_hands_standard_deviation_rank(self):
        return self.all_hands_statistics["standard_deviation_rank"]

    def rank_deviation(self, cards):
        """Concrete rank's signed deviation from the population mean, not variance."""
        return self[cards] - self.all_hands_average_rank

    def __len__(self):
        return HAND_COUNT

    def __iter__(self):
        # IDs are accepted as keys; no giant list is allocated.
        return combinations(range(52), 7)

    def close(self):
        self._map.close()
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
