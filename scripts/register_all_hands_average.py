import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from poker_evaluator.seven_card_dictionary import DEFAULT_DIRECTORY
from poker_evaluator.rank_statistics import register_all_hands_average

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scan every explicit seven-card hand and register its population mean rank')
    parser.add_argument('--dictionary', type=Path, default=DEFAULT_DIRECTORY)
    args = parser.parse_args()
    result = register_all_hands_average(args.dictionary)
    print(json.dumps({k: v for k, v in result.items() if k != 'rank_counts'}, indent=2))
