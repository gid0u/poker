import json
from functools import lru_cache
from pathlib import Path

from poker_evaluator.cards import Card
from poker_evaluator.evaluate5 import HandValue, evaluate5
from poker_evaluator.evaluate7 import evaluate7


RANK_TABLE_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "processed"
    / "five_card_rank_table.json"
)


@lru_cache(maxsize=1)
def load_rank_table() -> dict[HandValue, int]:
    """JSONから7462役クラスの順位表を読み込む。"""

    if not RANK_TABLE_PATH.exists():
        raise FileNotFoundError(f"順位表が見つかりません: {RANK_TABLE_PATH}")

    with RANK_TABLE_PATH.open("r", encoding="utf-8") as file:
        raw_values = json.load(file)

    ordered_values: list[HandValue] = [tuple(value) for value in raw_values]

    if len(ordered_values) != 7_462:
        raise ValueError(f"順位表の役クラス数が不正です: {len(ordered_values)}")

    return {value: rank for rank, value in enumerate(ordered_values, start=1)}


def rank_from_value(value: HandValue) -> int:
    """5枚役の評価タプルを1〜7462位へ変換する。"""

    rank_table = load_rank_table()

    try:
        return rank_table[value]
    except KeyError as error:
        raise ValueError(f"順位表に存在しない評価タプルです: {value}") from error


def rank_five_cards(cards: list[Card]) -> int:
    """5枚のカードを評価し、1〜7462の順位を返す。"""

    value = evaluate5(cards)

    return rank_from_value(value)


def rank_seven_cards(cards: list[Card]) -> int:
    """7枚から最強の5枚役を選び、1〜7462の順位を返す。"""

    value = evaluate7(cards)

    return rank_from_value(value)
