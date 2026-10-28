"""Exact integration examples including the complete C(52,7) distribution."""
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary, HAND_COUNT


def main():
    results = []
    with SevenCardRankDictionary() as table:
        for pattern, weights in (("As Ks Qs Js 2c 3d X1s", None),
                                  ("As Ks Qs Js 2c 3d X1s", {"Ts": 5}),
                                  ("As Ks Qo Jo 9s 8s 7s", None),
                                  ("As Qo Qp Js 9s 8s 7s", None),
                                  ("X1 X2 X3 X4 X5 X6 X7", None)):
            result = table.evaluate_wildcards(pattern, card_weights=weights)
            results.append(asdict(result))
            print(f"{result.normalized}: {result.legal_hands:,} hands; mean rank={result.mean_rank:.6f}")
    assert results[0]["legal_hands"] == 9
    assert results[1]["total_weight"] == 13
    assert results[1]["mean_rank"] < results[0]["mean_rank"]
    assert results[2]["legal_hands"] == 3
    assert results[3]["legal_hands"] == 3
    assert results[4]["legal_hands"] == HAND_COUNT
    verification = json.loads((ROOT / "results/seven_card_dictionary_verification.json").read_text())
    for category, count in verification["category_counts"].items():
        assert abs(results[4]["category_probabilities"][category]-count/HAND_COUNT) < 1e-12
    (ROOT / "results/wildcard_examples.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
