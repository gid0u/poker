from poker_evaluator.cards import parse_card
from poker_evaluator.equity import calculate_exact_equity


def main() -> None:
    player1_hole = [
        parse_card("As"),
        parse_card("Ah"),
    ]

    player2_hole = [
        parse_card("Ks"),
        parse_card("Kh"),
    ]

    board_cards = [
        parse_card("2c"),
        parse_card("7d"),
        parse_card("9s"),
        parse_card("Jc"),
    ]

    result = calculate_exact_equity(
        player1_hole,
        player2_hole,
        board_cards,
    )

    print("AA vs KK")
    print("Board: 2c 7d 9s Jc")
    print("-" * 30)
    print(f"Player 1 wins: {result.player1_wins}")
    print(f"Player 2 wins: {result.player2_wins}")
    print(f"Ties:          {result.ties}")
    print(f"Total:         {result.total}")
    print("-" * 30)
    print(f"Player 1 equity: {result.player1_equity:.2%}")
    print(f"Player 2 equity: {result.player2_equity:.2%}")


if __name__ == "__main__":
    main()
