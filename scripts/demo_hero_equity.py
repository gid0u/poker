from poker_evaluator.cards import parse_card
from poker_evaluator.equity import calculate_hero_equity_vs_random


def main() -> None:
    hero_hole = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    result = calculate_hero_equity_vs_random(
        hero_hole=hero_hole,
        opponent_count=3,
        board_cards=[],
        iterations=20_000,
        seed=2026,
    )

    print("Hero: As Ah")
    print("Opponents: 3 random players")
    print("Board: preflop")
    print("-" * 36)

    print(f"Outright wins: {result.outright_wins:,}")
    print(f"Tie participations: {result.tie_participations:,}")
    print(f"Losses: {result.losses:,}")
    print(f"Total: {result.total:,}")

    print("-" * 36)

    print(f"Win rate:  {result.win_rate:.2%}")
    print(f"Tie rate:  {result.tie_rate:.2%}")
    print(f"Loss rate: {result.loss_rate:.2%}")
    print(f"Equity:    {result.equity:.2%}")

    assert (
        result.outright_wins + result.tie_participations + result.losses == result.total
    )

    assert abs(result.win_rate + result.tie_rate + result.loss_rate - 1.0) < 1e-12


if __name__ == "__main__":
    main()
