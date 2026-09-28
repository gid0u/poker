import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from time import perf_counter

from poker_evaluator.cards import create_deck
from poker_evaluator.evaluate5 import HandValue, evaluate5


EXPECTED_CLASS_COUNTS = Counter(
    {
        8: 10,
        7: 156,
        6: 156,
        5: 1_277,
        4: 10,
        3: 858,
        2: 858,
        1: 2_860,
        0: 1_277,
    }
)


def main() -> None:
    deck = create_deck()
    unique_values: set[HandValue] = set()

    started_at = perf_counter()

    for processed, hand in enumerate(combinations(deck, 5), start=1):
        unique_values.add(evaluate5(list(hand)))

        if processed % 250_000 == 0:
            print(f"{processed:,} hands processed")

    elapsed = perf_counter() - started_at

    # 評価タプルを強い順に並べる
    ordered_values = sorted(unique_values, reverse=True)

    # 最強を1位として順位を付ける
    rank_table = {value: rank for rank, value in enumerate(ordered_values, start=1)}

    # 順位表をJSONファイルとして保存する
    output_path = Path("data/processed/five_card_rank_table.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(
            [list(value) for value in ordered_values],
            file,
            ensure_ascii=False,
            indent=2,
        )

    class_counts = Counter(value[0] for value in unique_values)

    print()
    print("Five-card rank-class results")
    print("-" * 40)

    for category in range(8, -1, -1):
        actual = class_counts[category]
        expected = EXPECTED_CLASS_COUNTS[category]
        status = "OK" if actual == expected else "ERROR"

        print(
            f"category={category} classes={actual:>5,} expected={expected:>5,} {status}"
        )

    strongest = ordered_values[0]
    weakest = ordered_values[-1]

    baseline = (0, 14, 13, 12, 11, 7)
    baseline_rank = rank_table[baseline]

    print("-" * 40)
    print(f"Total classes: {len(unique_values):,}")
    print(f"Strongest:     {strongest}")
    print(f"Weakest:       {weakest}")
    print(f"AKQJ7 high:    rank {baseline_rank:,}")
    print(f"Saved to:      {output_path}")
    print(f"Elapsed:       {elapsed:.2f} seconds")

    assert len(unique_values) == 7_462
    assert class_counts == EXPECTED_CLASS_COUNTS

    assert strongest == (8, 14)
    assert rank_table[strongest] == 1

    assert weakest == (0, 7, 5, 4, 3, 2)
    assert rank_table[weakest] == 7_462

    assert baseline_rank == 6_188

    print()
    print("All 7,462 five-card rank classes are correct.")


if __name__ == "__main__":
    main()
