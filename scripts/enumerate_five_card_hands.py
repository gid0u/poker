from collections import Counter
from itertools import combinations
from time import perf_counter

from poker_evaluator.cards import create_deck
from poker_evaluator.evaluate5 import evaluate5


TOTAL_HANDS = 2_598_960

CATEGORY_NAMES = {
    8: "straight flush",
    7: "four of a kind",
    6: "full house",
    5: "flush",
    4: "straight",
    3: "three of a kind",
    2: "two pair",
    1: "one pair",
    0: "high card",
}

EXPECTED_COUNTS = Counter(
    {
        8: 40,
        7: 624,
        6: 3_744,
        5: 5_108,
        4: 10_200,
        3: 54_912,
        2: 123_552,
        1: 1_098_240,
        0: 1_302_540,
    }
)


def main() -> None:
    deck = create_deck()
    counts: Counter[int] = Counter()

    started_at = perf_counter()
    processed = 0

    for processed, hand in enumerate(combinations(deck, 5), start=1):
        value = evaluate5(list(hand))
        category = value[0]

        counts[category] += 1

        if processed % 250_000 == 0:
            print(f"{processed:,} / {TOTAL_HANDS:,} hands processed")

    elapsed = perf_counter() - started_at

    print()
    print("Five-card hand enumeration results")
    print("-" * 45)

    for category in range(8, -1, -1):
        name = CATEGORY_NAMES[category]
        actual = counts[category]
        expected = EXPECTED_COUNTS[category]
        status = "OK" if actual == expected else "ERROR"

        print(f"{category}: {name:<16} {actual:>10,} expected={expected:>10,} {status}")

    print("-" * 45)
    print(f"Total:   {processed:,}")
    print(f"Elapsed: {elapsed:.2f} seconds")

    assert processed == TOTAL_HANDS
    assert counts == EXPECTED_COUNTS

    print()
    print("All five-card category counts are correct.")


if __name__ == "__main__":
    main()
