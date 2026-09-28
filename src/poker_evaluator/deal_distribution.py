from __future__ import annotations

from collections.abc import Iterable, Sequence

from .cards import Card, parse_card
from .chance import (
    ChanceDistribution,
    ChanceOutcome,
)
from .game_state import (
    GameState,
    PlayerState,
    Street,
)
from .range_parser import (
    HandCombo,
    parse_range,
    remove_blocked_combos,
)


CardInput = Card | str
RangeInput = str | Iterable[HandCombo]


def _normalize_card(
    card: CardInput,
) -> Card:
    if isinstance(card, Card):
        return card

    if isinstance(card, str):
        return parse_card(card)

    raise TypeError("カードはCardまたは文字列で指定してください。")


def _normalize_board(
    board: Iterable[CardInput],
) -> tuple[Card, ...]:
    normalized = tuple(_normalize_card(card) for card in board)

    if len(set(normalized)) != len(normalized):
        raise ValueError("ボードに重複したカードがあります。")

    return normalized


def _normalize_range(
    range_value: RangeInput,
) -> tuple[HandCombo, ...]:
    if isinstance(range_value, str):
        return parse_range(range_value)

    combos = tuple(range_value)

    if not combos:
        raise ValueError("レンジにコンボがありません。")

    for combo in combos:
        if not isinstance(combo, HandCombo):
            raise TypeError("レンジにはHandComboだけを含めてください。")

    seen: set[frozenset[Card]] = set()
    unique_combos: list[HandCombo] = []

    for combo in combos:
        normalized = combo.normalized()

        if normalized in seen:
            continue

        seen.add(normalized)
        unique_combos.append(combo)

    return tuple(unique_combos)


def _validate_stacks(
    stacks: Sequence[int],
) -> tuple[int, int]:
    if len(stacks) != 2:
        raise ValueError("スタックは2人分指定してください。")

    p0_stack = stacks[0]
    p1_stack = stacks[1]

    if not isinstance(p0_stack, int):
        raise TypeError("P0のスタックは整数で指定してください。")

    if not isinstance(p1_stack, int):
        raise TypeError("P1のスタックは整数で指定してください。")

    if p0_stack < 0 or p1_stack < 0:
        raise ValueError("スタックを負の値にはできません。")

    return p0_stack, p1_stack


def _format_combo(
    combo: HandCombo,
) -> str:
    return f"{combo.first}{combo.second}"


def combos_overlap(
    first: HandCombo,
    second: HandCombo,
) -> bool:
    """
    2つのホールカードコンボが
    同じ実カードを含むか判定する。
    """
    return bool(first.normalized() & second.normalized())


def generate_legal_matchups(
    p0_range: RangeInput,
    p1_range: RangeInput,
    board: Iterable[CardInput] = (),
) -> tuple[
    tuple[HandCombo, HandCombo],
    ...,
]:
    """
    両プレイヤーのレンジから、
    カード重複のない配布だけを生成する。

    除外対象:
    - ボードとP0の重複
    - ボードとP1の重複
    - P0とP1の重複
    """
    normalized_board = _normalize_board(board)

    p0_combos = remove_blocked_combos(
        _normalize_range(p0_range),
        normalized_board,
    )

    p1_combos = remove_blocked_combos(
        _normalize_range(p1_range),
        normalized_board,
    )

    matchups: list[tuple[HandCombo, HandCombo]] = []

    for p0_combo in p0_combos:
        for p1_combo in p1_combos:
            if combos_overlap(
                p0_combo,
                p1_combo,
            ):
                continue

            matchups.append(
                (
                    p0_combo,
                    p1_combo,
                )
            )

    return tuple(matchups)


def create_state_from_matchup(
    p0_combo: HandCombo,
    p1_combo: HandCombo,
    *,
    board: Iterable[CardInput],
    stacks: Sequence[int] = (100, 100),
    pot: int = 100,
    acting_player_index: int = 0,
    street: Street = Street.RIVER,
) -> GameState:
    """
    1組の合法なホールカード配布から
    GameStateを生成する。
    """
    normalized_board = _normalize_board(board)
    p0_stack, p1_stack = _validate_stacks(stacks)

    if not isinstance(pot, int):
        raise TypeError("ポットは整数で指定してください。")

    if pot < 0:
        raise ValueError("ポットを負の値にはできません。")

    if acting_player_index not in (0, 1):
        raise ValueError("acting_player_indexは0または1です。")

    if p0_combo.overlaps(normalized_board):
        raise ValueError("P0のホールカードがボードと重複しています。")

    if p1_combo.overlaps(normalized_board):
        raise ValueError("P1のホールカードがボードと重複しています。")

    if combos_overlap(
        p0_combo,
        p1_combo,
    ):
        raise ValueError("両プレイヤーのホールカードが重複しています。")

    return GameState(
        players=[
            PlayerState(
                player_id=0,
                stack=p0_stack,
                hole_cards=p0_combo.cards,
            ),
            PlayerState(
                player_id=1,
                stack=p1_stack,
                hole_cards=p1_combo.cards,
            ),
        ],
        pot=pot,
        acting_player_index=acting_player_index,
        board=normalized_board,
        street=street,
    )


def build_deal_distribution(
    p0_range: RangeInput,
    p1_range: RangeInput,
    *,
    board: Iterable[CardInput],
    stacks: Sequence[int] = (100, 100),
    pot: int = 100,
    acting_player_index: int = 0,
    street: Street = Street.RIVER,
) -> ChanceDistribution:
    """
    2人のレンジから合法なカード配布を列挙し、
    一様確率のChanceDistributionを生成する。

    現段階では各コンボに重みを付けず、
    すべての合法な配布を等確率とする。
    """
    normalized_board = _normalize_board(board)

    matchups = generate_legal_matchups(
        p0_range=p0_range,
        p1_range=p1_range,
        board=normalized_board,
    )

    if not matchups:
        raise ValueError("合法なカード配布が1つもありません。")

    probability = 1.0 / len(matchups)

    outcomes: list[ChanceOutcome] = []

    for p0_combo, p1_combo in matchups:
        state = create_state_from_matchup(
            p0_combo,
            p1_combo,
            board=normalized_board,
            stacks=stacks,
            pot=pot,
            acting_player_index=(acting_player_index),
            street=street,
        )

        outcomes.append(
            ChanceOutcome(
                state=state,
                probability=probability,
                label=(f"P0={_format_combo(p0_combo)}|P1={_format_combo(p1_combo)}"),
            )
        )

    return ChanceDistribution.create(outcomes)
