import random
from dataclasses import dataclass
from itertools import combinations

from poker_evaluator.cards import Card, create_deck
from poker_evaluator.showdown import (
    ShowdownResult,
    compare_holdem,
    compare_multiway_holdem,
)

from poker_evaluator.ranges import (
    filter_blocked_combos,
    parse_range,
)


@dataclass(frozen=True)
class EquityResult:
    """2人の勝敗回数とエクイティ計算結果。"""

    player1_wins: int
    player2_wins: int
    ties: int
    total: int

    @property
    def player1_equity(self) -> float:
        """引き分けを半分ずつ分配したプレイヤー1のエクイティ。"""

        return (self.player1_wins + self.ties / 2) / self.total

    @property
    def player2_equity(self) -> float:
        """引き分けを半分ずつ分配したプレイヤー2のエクイティ。"""

        return (self.player2_wins + self.ties / 2) / self.total


@dataclass(frozen=True)
class MultiwayEquityResult:
    """複数人の勝敗回数とポット取得割合。"""

    outright_wins: tuple[int, ...]
    tie_participations: tuple[int, ...]
    share_totals: tuple[float, ...]
    total: int

    @property
    def equities(self) -> tuple[float, ...]:
        """各プレイヤーの平均ポット取得割合を返す。"""

        return tuple(share_total / self.total for share_total in self.share_totals)


@dataclass(frozen=True)
class HeroEquityResult:
    """未知の相手に対するHero視点の計算結果。"""

    outright_wins: int
    tie_participations: int
    losses: int
    share_total: float
    total: int

    @property
    def equity(self) -> float:
        """Heroの平均ポット取得割合を返す。"""

        return self.share_total / self.total

    @property
    def win_rate(self) -> float:
        """単独勝利率を返す。"""

        return self.outright_wins / self.total

    @property
    def tie_rate(self) -> float:
        """引き分け参加率を返す。"""

        return self.tie_participations / self.total

    @property
    def loss_rate(self) -> float:
        """敗北率を返す。"""

        return self.losses / self.total


def calculate_exact_equity(
    player1_hole: list[Card],
    player2_hole: list[Card],
    board_cards: list[Card],
) -> EquityResult:
    """残りのボードを全列挙し、正確なヘッズアップエクイティを返す。"""

    if len(player1_hole) != 2:
        raise ValueError(
            f"プレイヤー1のホールカードは2枚必要です。入力枚数: {len(player1_hole)}"
        )

    if len(player2_hole) != 2:
        raise ValueError(
            f"プレイヤー2のホールカードは2枚必要です。入力枚数: {len(player2_hole)}"
        )

    if len(board_cards) not in {3, 4, 5}:
        raise ValueError(
            "ボードカードはフロップ以降の3〜5枚で入力してください。"
            f"入力枚数: {len(board_cards)}"
        )

    known_cards = player1_hole + player2_hole + board_cards

    if len(set(known_cards)) != len(known_cards):
        raise ValueError("既知のカードに重複があります")

    known_set = set(known_cards)

    remaining_deck = [card for card in create_deck() if card not in known_set]

    missing_board_cards = 5 - len(board_cards)

    player1_wins = 0
    player2_wins = 0
    ties = 0

    for runout in combinations(
        remaining_deck,
        missing_board_cards,
    ):
        complete_board = board_cards + list(runout)

        result = compare_holdem(
            player1_hole,
            player2_hole,
            complete_board,
        )

        if result is ShowdownResult.PLAYER1_WIN:
            player1_wins += 1
        elif result is ShowdownResult.PLAYER2_WIN:
            player2_wins += 1
        else:
            ties += 1

    total = player1_wins + player2_wins + ties

    return EquityResult(
        player1_wins=player1_wins,
        player2_wins=player2_wins,
        ties=ties,
        total=total,
    )


def calculate_monte_carlo_equity(
    player1_hole: list[Card],
    player2_hole: list[Card],
    board_cards: list[Card],
    iterations: int = 10_000,
    seed: int | None = None,
) -> EquityResult:
    """無作為なランアウトを生成してヘッズアップエクイティを推定する。"""

    if len(player1_hole) != 2:
        raise ValueError(
            f"プレイヤー1のホールカードは2枚必要です。入力枚数: {len(player1_hole)}"
        )

    if len(player2_hole) != 2:
        raise ValueError(
            f"プレイヤー2のホールカードは2枚必要です。入力枚数: {len(player2_hole)}"
        )

    if len(board_cards) not in {0, 3, 4, 5}:
        raise ValueError(
            "ボードカードはプリフロップの0枚、"
            "またはフロップ以降の3〜5枚で入力してください。"
            f"入力枚数: {len(board_cards)}"
        )

    if iterations <= 0:
        raise ValueError(f"試行回数は1以上である必要があります: {iterations}")

    known_cards = player1_hole + player2_hole + board_cards

    if len(set(known_cards)) != len(known_cards):
        raise ValueError("既知のカードに重複があります")

    known_set = set(known_cards)

    remaining_deck = [card for card in create_deck() if card not in known_set]

    missing_board_cards = 5 - len(board_cards)
    rng = random.Random(seed)

    player1_wins = 0
    player2_wins = 0
    ties = 0

    for _ in range(iterations):
        runout = rng.sample(
            remaining_deck,
            missing_board_cards,
        )

        complete_board = board_cards + runout

        result = compare_holdem(
            player1_hole,
            player2_hole,
            complete_board,
        )

        if result is ShowdownResult.PLAYER1_WIN:
            player1_wins += 1
        elif result is ShowdownResult.PLAYER2_WIN:
            player2_wins += 1
        else:
            ties += 1

    return EquityResult(
        player1_wins=player1_wins,
        player2_wins=player2_wins,
        ties=ties,
        total=iterations,
    )


def calculate_hero_equity_vs_random(
    hero_hole: list[Card],
    opponent_count: int,
    board_cards: list[Card],
    iterations: int = 10_000,
    seed: int | None = None,
) -> HeroEquityResult:
    """未知の相手へ無作為にカードを配り、Heroのエクイティを推定する。"""

    if len(hero_hole) != 2:
        raise ValueError(f"Heroのホールカードは2枚必要です。入力枚数: {len(hero_hole)}")

    if opponent_count < 1:
        raise ValueError(f"相手は1人以上必要です。入力人数: {opponent_count}")

    if len(board_cards) not in {0, 3, 4, 5}:
        raise ValueError(
            "ボードカードはプリフロップの0枚、"
            "またはフロップ以降の3〜5枚で入力してください。"
            f"入力枚数: {len(board_cards)}"
        )

    if iterations <= 0:
        raise ValueError(f"試行回数は1以上である必要があります: {iterations}")

    known_cards = hero_hole + board_cards

    if len(set(known_cards)) != len(known_cards):
        raise ValueError("Heroのカードまたはボードに重複があります")

    known_set = set(known_cards)

    remaining_deck = [card for card in create_deck() if card not in known_set]

    missing_board_cards = 5 - len(board_cards)

    required_unknown_cards = opponent_count * 2 + missing_board_cards

    if required_unknown_cards > len(remaining_deck):
        raise ValueError("指定された人数へ配るためのカードが不足しています")

    rng = random.Random(seed)

    outright_wins = 0
    tie_participations = 0
    losses = 0
    share_total = 0.0

    for _ in range(iterations):
        dealt_cards = rng.sample(
            remaining_deck,
            required_unknown_cards,
        )

        opponent_holes = [
            dealt_cards[index * 2 : index * 2 + 2] for index in range(opponent_count)
        ]

        board_start = opponent_count * 2

        runout = dealt_cards[board_start:]

        complete_board = board_cards + runout

        player_holes = [
            hero_hole,
            *opponent_holes,
        ]

        result = compare_multiway_holdem(
            player_holes,
            complete_board,
        )

        winners = result.winner_indices

        if 0 not in winners:
            losses += 1
            continue

        share_total += 1.0 / len(winners)

        if len(winners) == 1:
            outright_wins += 1
        else:
            tie_participations += 1

    return HeroEquityResult(
        outright_wins=outright_wins,
        tie_participations=tie_participations,
        losses=losses,
        share_total=share_total,
        total=iterations,
    )


def calculate_multiway_exact_equity(
    player_holes: list[list[Card]],
    board_cards: list[Card],
) -> MultiwayEquityResult:
    """残りボードを全列挙して複数人の正確なエクイティを返す。"""

    if len(player_holes) < 2:
        raise ValueError(f"プレイヤーは2人以上必要です。入力人数: {len(player_holes)}")

    for player_number, hole_cards in enumerate(
        player_holes,
        start=1,
    ):
        if len(hole_cards) != 2:
            raise ValueError(
                f"プレイヤー{player_number}のホールカードは"
                f"2枚必要です。入力枚数: {len(hole_cards)}"
            )

    if len(board_cards) not in {3, 4, 5}:
        raise ValueError(
            "ボードカードはフロップ以降の3〜5枚で入力してください。"
            f"入力枚数: {len(board_cards)}"
        )

    known_cards = [
        card for hole_cards in player_holes for card in hole_cards
    ] + board_cards

    if len(set(known_cards)) != len(known_cards):
        raise ValueError("既知のカードに重複があります")

    known_set = set(known_cards)

    remaining_deck = [card for card in create_deck() if card not in known_set]

    missing_board_cards = 5 - len(board_cards)
    player_count = len(player_holes)

    outright_wins = [0] * player_count
    tie_participations = [0] * player_count
    share_totals = [0.0] * player_count
    total = 0

    for runout in combinations(
        remaining_deck,
        missing_board_cards,
    ):
        complete_board = board_cards + list(runout)

        result = compare_multiway_holdem(
            player_holes,
            complete_board,
        )

        winners = result.winner_indices
        pot_share = 1.0 / len(winners)

        if len(winners) == 1:
            outright_wins[winners[0]] += 1
        else:
            for winner_index in winners:
                tie_participations[winner_index] += 1

        for winner_index in winners:
            share_totals[winner_index] += pot_share

        total += 1

    return MultiwayEquityResult(
        outright_wins=tuple(outright_wins),
        tie_participations=tuple(tie_participations),
        share_totals=tuple(share_totals),
        total=total,
    )


def calculate_hero_equity_vs_range(
    hero_hole: list[Card],
    opponent_range: str,
    board_cards: list[Card],
    iterations: int = 10_000,
    seed: int | None = None,
) -> HeroEquityResult:
    """指定レンジの相手1人に対するHeroのエクイティを推定する。"""

    if len(hero_hole) != 2:
        raise ValueError(f"Heroのホールカードは2枚必要です。入力枚数: {len(hero_hole)}")

    if len(board_cards) not in {0, 3, 4, 5}:
        raise ValueError(
            "ボードカードはプリフロップの0枚、"
            "またはフロップ以降の3〜5枚で入力してください。"
            f"入力枚数: {len(board_cards)}"
        )

    if iterations <= 0:
        raise ValueError(f"試行回数は1以上である必要があります: {iterations}")

    known_cards = hero_hole + board_cards

    if len(set(known_cards)) != len(known_cards):
        raise ValueError("Heroのカードまたはボードに重複があります")

    range_combos = parse_range(opponent_range)

    available_combos = filter_blocked_combos(
        range_combos,
        known_cards,
    )

    if not available_combos:
        raise ValueError("既知カードによって相手レンジの全コンボがブロックされています")

    known_set = set(known_cards)
    full_deck = create_deck()
    missing_board_cards = 5 - len(board_cards)

    rng = random.Random(seed)

    outright_wins = 0
    tie_participations = 0
    losses = 0
    share_total = 0.0

    for _ in range(iterations):
        opponent_combo = rng.choice(available_combos)

        occupied_cards = known_set | set(opponent_combo)

        remaining_deck = [card for card in full_deck if card not in occupied_cards]

        runout = rng.sample(
            remaining_deck,
            missing_board_cards,
        )

        complete_board = board_cards + runout

        result = compare_multiway_holdem(
            [
                hero_hole,
                list(opponent_combo),
            ],
            complete_board,
        )

        winners = result.winner_indices

        if 0 not in winners:
            losses += 1
            continue

        share_total += 1.0 / len(winners)

        if len(winners) == 1:
            outright_wins += 1
        else:
            tie_participations += 1

    return HeroEquityResult(
        outright_wins=outright_wins,
        tie_participations=tie_participations,
        losses=losses,
        share_total=share_total,
        total=iterations,
    )


def calculate_hero_exact_equity_vs_range(
    hero_hole: list[Card],
    opponent_range: str,
    board_cards: list[Card],
) -> HeroEquityResult:
    """指定レンジの相手1人に対するHeroの正確なエクイティを返す。"""

    if len(hero_hole) != 2:
        raise ValueError(f"Heroのホールカードは2枚必要です。入力枚数: {len(hero_hole)}")

    if len(board_cards) not in {3, 4, 5}:
        raise ValueError(
            "正確なレンジ計算では、ボードカードを"
            "フロップ以降の3〜5枚で入力してください。"
            f"入力枚数: {len(board_cards)}"
        )

    known_cards = hero_hole + board_cards

    if len(set(known_cards)) != len(known_cards):
        raise ValueError("Heroのカードまたはボードに重複があります")

    range_combos = parse_range(opponent_range)

    available_combos = filter_blocked_combos(
        range_combos,
        known_cards,
    )

    if not available_combos:
        raise ValueError("既知カードによって相手レンジの全コンボがブロックされています")

    known_set = set(known_cards)
    full_deck = create_deck()
    missing_board_cards = 5 - len(board_cards)

    outright_wins = 0
    tie_participations = 0
    losses = 0
    share_total = 0.0
    total = 0

    for opponent_combo in available_combos:
        occupied_cards = known_set | set(opponent_combo)

        remaining_deck = [card for card in full_deck if card not in occupied_cards]

        for runout in combinations(
            remaining_deck,
            missing_board_cards,
        ):
            complete_board = board_cards + list(runout)

            result = compare_multiway_holdem(
                [
                    hero_hole,
                    list(opponent_combo),
                ],
                complete_board,
            )

            winners = result.winner_indices

            if 0 not in winners:
                losses += 1
            else:
                share_total += 1.0 / len(winners)

                if len(winners) == 1:
                    outright_wins += 1
                else:
                    tie_participations += 1

            total += 1

    return HeroEquityResult(
        outright_wins=outright_wins,
        tie_participations=tie_participations,
        losses=losses,
        share_total=share_total,
        total=total,
    )
