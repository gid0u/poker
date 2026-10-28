import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from poker_evaluator.seven_card_dictionary import DEFAULT_DIRECTORY
from poker_evaluator.seven_card_builder import build, verify, atomic_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build/verify all 133,784,560 seven-card hand ranks")
    parser.add_argument("--output", type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument("--chunk-size", type=int, default=250000)
    parser.add_argument("--oracle-samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if args.verify_only:
        result = verify(args.output, oracle_samples=args.oracle_samples, seed=args.seed)
        atomic_json(args.output / "verification.json", result)
    else:
        result = build(args.output, chunk_size=args.chunk_size, oracle_samples=args.oracle_samples, seed=args.seed)
    print(json.dumps(result, indent=2))
