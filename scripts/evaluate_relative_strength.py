import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from poker_evaluator.seven_card_dictionary import SevenCardRankDictionary, DEFAULT_DIRECTORY

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Conditional rank dispersion and showdown equity')
    parser.add_argument('--hero', default='')
    parser.add_argument('--board', default='')
    parser.add_argument('--opponent', action='append', required=True, help='One range per opponent; repeat flag')
    parser.add_argument('--dead', default='')
    parser.add_argument('--pattern', help='Exact seven-token wildcard pattern: hero2/flop3/turn/river')
    parser.add_argument('--mode', choices=['exact', 'sampling'], default='sampling')
    parser.add_argument('--samples', type=int, default=10000)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--dictionary', type=Path, default=DEFAULT_DIRECTORY)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with SevenCardRankDictionary(args.dictionary) as table:
        if args.pattern:
            if args.mode != 'exact':
                parser.error('--pattern requires --mode exact')
            result = table.relative_wildcards(args.pattern, args.opponent, dead_cards=args.dead)
        else:
            result = table.relative_strength(args.hero, args.board, args.opponent,
                dead_cards=args.dead, mode=args.mode, samples=args.samples, seed=args.seed)
    text = json.dumps(asdict(result), indent=2)
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    print(text)
