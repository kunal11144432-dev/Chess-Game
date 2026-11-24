import unittest

from chess_game import ChessGame, parse_square


def play(game: ChessGame, start: str, end: str, promotion: str | None = None) -> None:
    start_square = parse_square(start)
    end_square = parse_square(end)
    move = next(
        move
        for move in game.legal_moves_from(start_square)
        if move.end == end_square and move.promotion == promotion
    )
    game.play_move(move)


class ChessRulesTests(unittest.TestCase):
    def set_position(
        self, game: ChessGame, pieces: dict[str, str], turn: str
    ) -> None:
        game.board = ["."] * 64
        for square, piece in pieces.items():
            game.board[parse_square(square)] = piece
        game.turn = turn
        game.castling_rights.clear()
        game.en_passant_square = None
        game.position_counts.clear()
        game._record_position()

    def test_initial_position_has_twenty_legal_moves(self) -> None:
        self.assertEqual(len(ChessGame().legal_moves()), 20)

    def test_checkmate_is_detected(self) -> None:
        game = ChessGame()
        for start, end in (
            ("f2", "f3"),
            ("e7", "e5"),
            ("g2", "g4"),
            ("d8", "h4"),
        ):
            play(game, start, end)
        self.assertEqual(game.status(), "Checkmate - Black wins!")

    def test_en_passant_removes_the_captured_pawn(self) -> None:
        game = ChessGame()
        for start, end in (
            ("e2", "e4"),
            ("a7", "a6"),
            ("e4", "e5"),
            ("d7", "d5"),
        ):
            play(game, start, end)
        play(game, "e5", "d6")
        self.assertEqual(game.board[parse_square("d5")], ".")
        self.assertEqual(game.board[parse_square("d6")], "P")

    def test_castling_moves_the_rook(self) -> None:
        game = ChessGame()
        for start, end in (
            ("e2", "e4"),
            ("e7", "e5"),
            ("g1", "f3"),
            ("b8", "c6"),
            ("f1", "e2"),
            ("g8", "f6"),
        ):
            play(game, start, end)
        play(game, "e1", "g1")
        self.assertEqual(game.board[parse_square("g1")], "K")
        self.assertEqual(game.board[parse_square("f1")], "R")

    def test_pawn_can_promote_to_a_chosen_piece(self) -> None:
        game = ChessGame()
        self.set_position(game, {"a1": "K", "h8": "k", "b7": "P"}, "w")
        play(game, "b7", "b8", promotion="N")
        self.assertEqual(game.board[parse_square("b8")], "N")

    def test_pinned_rook_cannot_expose_its_king(self) -> None:
        game = ChessGame()
        self.set_position(
            game,
            {"e1": "K", "a8": "k", "e8": "r", "e2": "R"},
            "w",
        )
        legal_destinations = {
            move.end for move in game.legal_moves_from(parse_square("e2"))
        }
        self.assertNotIn(parse_square("d2"), legal_destinations)
        self.assertIn(parse_square("e3"), legal_destinations)

    def test_stalemate_is_detected(self) -> None:
        game = ChessGame()
        self.set_position(
            game,
            {"h8": "k", "f7": "K", "g6": "Q"},
            "b",
        )
        self.assertEqual(game.status(), "Draw by stalemate.")


if __name__ == "__main__":
    unittest.main()
