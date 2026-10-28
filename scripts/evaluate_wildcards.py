import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from poker_evaluator.seven_card_dictionary import DEFAULT_DIRECTORY, SevenCardRankDictionary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exact wildcard conditional weighted hand strength")
    parser.add_argument("pattern", help='Seven tokens, e.g. "As Ks Qs Js 2c 3d X1s"')
    parser.add_argument("--dictionary", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--dead", nargs="*", default=[])
    parser.add_argument("--card-weights", type=Path, help="JSON file mapping actual cards to nonnegative weights")
    parser.add_argument("--max-candidates", type=int, default=1000000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    weights = json.loads(args.card_weights.read_text()) if args.card_weights else None
    with SevenCardRankDictionary(args.dictionary) as table:
        result = table.evaluate_wildcards(args.pattern, dead_cards=args.dead,
            card_weights=weights, max_candidates=args.max_candidates)
    text = json.dumps(asdict(result), indent=2)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text)
