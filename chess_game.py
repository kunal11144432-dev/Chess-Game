"""A two-player chess game built with Python's standard-library Tkinter."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox

FILES = "abcdefgh"
PIECE_GLYPHS = {
    "K": "\u2654",
    "Q": "\u2655",
    "R": "\u2656",
    "B": "\u2657",
    "N": "\u2658",
    "P": "\u2659",
    "k": "\u265a",
    "q": "\u265b",
    "r": "\u265c",
    "b": "\u265d",
    "n": "\u265e",
    "p": "\u265f",
}
PROMOTION_PIECES = ("Q", "R", "B", "N")


@dataclass(frozen=True)
class Move:
    start: int
    end: int
    promotion: str | None = None
    en_passant: bool = False
    castle: bool = False


def square_name(square: int) -> str:
    return f"{FILES[square % 8]}{8 - square // 8}"


def parse_square(name: str) -> int:
    if len(name) != 2 or name[0] not in FILES or name[1] not in "12345678":
        raise ValueError(f"Invalid square: {name}")
    return (8 - int(name[1])) * 8 + FILES.index(name[0])


class ChessGame:
    """Chess rules and position state, independent of the graphical interface."""

    def __init__(self) -> None:
        self.board = list(
            "rnbqkbnr"
            "pppppppp"
            "........"
            "........"
            "........"
            "........"
            "PPPPPPPP"
            "RNBQKBNR"
        )
        self.turn = "w"
        self.castling_rights = {"K", "Q", "k", "q"}
        self.en_passant_square: int | None = None
        self.halfmove_clock = 0
        self.position_counts: dict[tuple[object, ...], int] = {}
        self._record_position()

    @staticmethod
    def _is_white(piece: str) -> bool:
        return piece.isupper()

    @staticmethod
    def _inside(row: int, col: int) -> bool:
        return 0 <= row < 8 and 0 <= col < 8

    def _king_square(self, color: str) -> int:
        king = "K" if color == "w" else "k"
        try:
            return self.board.index(king)
        except ValueError as exc:
            raise ValueError(f"Position has no {color} king") from exc

    def is_square_attacked(self, square: int, by_color: str) -> bool:
        row, col = divmod(square, 8)
        pawn_row = row + (1 if by_color == "w" else -1)
        pawn = "P" if by_color == "w" else "p"
        for pawn_col in (col - 1, col + 1):
            if self._inside(pawn_row, pawn_col) and self.board[pawn_row * 8 + pawn_col] == pawn:
                return True

        knight = "N" if by_color == "w" else "n"
        for dr, dc in ((-2, -1), (-2, 1), (-1, -2), (-1, 2),
                       (1, -2), (1, 2), (2, -1), (2, 1)):
            r, c = row + dr, col + dc
            if self._inside(r, c) and self.board[r * 8 + c] == knight:
                return True

        king = "K" if by_color == "w" else "k"
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == dc == 0:
                    continue
                r, c = row + dr, col + dc
                if self._inside(r, c) and self.board[r * 8 + c] == king:
                    return True

        for directions, attackers in (
            (((-1, 0), (1, 0), (0, -1), (0, 1)), ("R", "Q")),
            (((-1, -1), (-1, 1), (1, -1), (1, 1)), ("B", "Q")),
        ):
            expected = {piece if by_color == "w" else piece.lower() for piece in attackers}
            for dr, dc in directions:
                r, c = row + dr, col + dc
                while self._inside(r, c):
                    piece = self.board[r * 8 + c]
                    if piece != ".":
                        if piece in expected:
                            return True
                        break
                    r += dr
                    c += dc
        return False

    def in_check(self, color: str) -> bool:
        return self.is_square_attacked(self._king_square(color), "b" if color == "w" else "w")

    def _pseudo_moves_from(self, start: int) -> list[Move]:
        piece = self.board[start]
        if piece == "." or self._is_white(piece) != (self.turn == "w"):
            return []

        row, col = divmod(start, 8)
        color = self.turn
        moves: list[Move] = []

        def add_if_available(r: int, c: int) -> bool:
            if not self._inside(r, c):
                return False
            end = r * 8 + c
            target = self.board[end]
            if target == ".":
                moves.append(Move(start, end))
                return True
            if self._is_white(target) != (color == "w") and target.lower() != "k":
                moves.append(Move(start, end))
            return False

        kind = piece.upper()
        if kind == "P":
            direction = -1 if color == "w" else 1
            last_row = 0 if color == "w" else 7
            next_row = row + direction
            if self._inside(next_row, col) and self.board[next_row * 8 + col] == ".":
                end = next_row * 8 + col
                moves.extend(
                    Move(start, end, promotion=promotion) for promotion in PROMOTION_PIECES
                ) if next_row == last_row else moves.append(Move(start, end))
                start_row = 6 if color == "w" else 1
                double_row = row + 2 * direction
                if row == start_row and self.board[double_row * 8 + col] == ".":
                    moves.append(Move(start, double_row * 8 + col))
            for dc in (-1, 1):
                capture_col = col + dc
                if not self._inside(next_row, capture_col):
                    continue
                end = next_row * 8 + capture_col
                target = self.board[end]
                if target != "." and self._is_white(target) != (color == "w") and target.lower() != "k":
                    if next_row == last_row:
                        moves.extend(
                            Move(start, end, promotion=promotion) for promotion in PROMOTION_PIECES
                        )
                    else:
                        moves.append(Move(start, end))
                elif end == self.en_passant_square:
                    moves.append(Move(start, end, en_passant=True))
        elif kind == "N":
            for dr, dc in ((-2, -1), (-2, 1), (-1, -2), (-1, 2),
                           (1, -2), (1, 2), (2, -1), (2, 1)):
                add_if_available(row + dr, col + dc)
        elif kind in ("B", "R", "Q"):
            directions = []
            if kind in ("B", "Q"):
                directions.extend(((-1, -1), (-1, 1), (1, -1), (1, 1)))
            if kind in ("R", "Q"):
                directions.extend(((-1, 0), (1, 0), (0, -1), (0, 1)))
            for dr, dc in directions:
                r, c = row + dr, col + dc
                while self._inside(r, c):
                    if not add_if_available(r, c):
                        break
                    r += dr
                    c += dc
        elif kind == "K":
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr != 0 or dc != 0:
                        add_if_available(row + dr, col + dc)
            self._add_castling_moves(start, moves)
        return moves

    def _add_castling_moves(self, start: int, moves: list[Move]) -> None:
        color = self.turn
        home_row = 7 if color == "w" else 0
        king = "K" if color == "w" else "k"
        rook = "R" if color == "w" else "r"
        enemy = "b" if color == "w" else "w"
        if start != home_row * 8 + 4 or self.board[start] != king or self.in_check(color):
            return
        for side, right, rook_col, transit_cols, empty_cols in (
            ("king", "K" if color == "w" else "k", 7, (5, 6), (5, 6)),
            ("queen", "Q" if color == "w" else "q", 0, (3, 2), (1, 2, 3)),
        ):
            if right not in self.castling_rights or self.board[home_row * 8 + rook_col] != rook:
                continue
            if any(self.board[home_row * 8 + c] != "." for c in empty_cols):
                continue
            if any(self.is_square_attacked(home_row * 8 + c, enemy) for c in transit_cols):
                continue
            king_col = 6 if side == "king" else 2
            moves.append(Move(start, home_row * 8 + king_col, castle=True))

    def legal_moves_from(self, start: int) -> list[Move]:
        legal = []
        mover = self.turn
        for move in self._pseudo_moves_from(start):
            snapshot = self._snapshot()
            self._apply_move(move)
            if not self.in_check(mover):
                legal.append(move)
            self._restore(snapshot)
        return legal

    def legal_moves(self) -> list[Move]:
        return [
            move
            for start, piece in enumerate(self.board)
            if piece != "." and self._is_white(piece) == (self.turn == "w")
            for move in self.legal_moves_from(start)
        ]

    def _snapshot(self) -> tuple[list[str], str, set[str], int | None, int]:
        return (
            self.board.copy(),
            self.turn,
            self.castling_rights.copy(),
            self.en_passant_square,
            self.halfmove_clock,
        )

    def _restore(self, snapshot: tuple[list[str], str, set[str], int | None, int]) -> None:
        (
            self.board,
            self.turn,
            self.castling_rights,
            self.en_passant_square,
            self.halfmove_clock,
        ) = snapshot

    def _apply_move(self, move: Move) -> None:
        piece = self.board[move.start]
        captured = self.board[move.end]
        start_row, start_col = divmod(move.start, 8)
        end_row, end_col = divmod(move.end, 8)
        self.board[move.start] = "."
        if move.en_passant:
            captured_square = move.end + (8 if self.turn == "w" else -8)
            captured = self.board[captured_square]
            self.board[captured_square] = "."
        self.board[move.end] = (
            move.promotion if self.turn == "w" else move.promotion.lower()
        ) if move.promotion else piece

        if move.castle:
            rook_start = start_row * 8 + (7 if end_col == 6 else 0)
            rook_end = start_row * 8 + (5 if end_col == 6 else 3)
            self.board[rook_end] = self.board[rook_start]
            self.board[rook_start] = "."

        if piece.upper() == "K":
            self.castling_rights.discard("K" if self.turn == "w" else "k")
            self.castling_rights.discard("Q" if self.turn == "w" else "q")
        if piece.upper() == "R":
            self._remove_rook_right(move.start)
        if captured.upper() == "R":
            self._remove_rook_right(move.end if not move.en_passant else move.end + (8 if self.turn == "w" else -8))

        self.en_passant_square = None
        if piece.upper() == "P" and abs(end_row - start_row) == 2:
            self.en_passant_square = (move.start + move.end) // 2
        self.halfmove_clock = 0 if piece.upper() == "P" or captured != "." else self.halfmove_clock + 1
        self.turn = "b" if self.turn == "w" else "w"

    def _remove_rook_right(self, square: int) -> None:
        rights_by_square = {63: "K", 56: "Q", 7: "k", 0: "q"}
        right = rights_by_square.get(square)
        if right:
            self.castling_rights.discard(right)

    def play_move(self, move: Move) -> None:
        if move not in self.legal_moves_from(move.start):
            raise ValueError("That move is not legal in the current position")
        self._apply_move(move)
        self._record_position()

    def _position_key(self) -> tuple[object, ...]:
        return (
            tuple(self.board),
            self.turn,
            tuple(sorted(self.castling_rights)),
            self.en_passant_square,
        )

    def _record_position(self) -> None:
        key = self._position_key()
        self.position_counts[key] = self.position_counts.get(key, 0) + 1

    def status(self) -> str:
        legal = self.legal_moves()
        if not legal:
            if self.in_check(self.turn):
                winner = "Black" if self.turn == "w" else "White"
                return f"Checkmate - {winner} wins!"
            return "Draw by stalemate."
        if self.halfmove_clock >= 100:
            return "Draw by the fifty-move rule."
        if self.position_counts.get(self._position_key(), 0) >= 3:
            return "Draw by threefold repetition."
        if self._insufficient_material():
            return "Draw by insufficient material."
        side = "White" if self.turn == "w" else "Black"
        return f"{side} to move" + (" - Check!" if self.in_check(self.turn) else "")

    def _insufficient_material(self) -> bool:
        pieces = [(i, p.upper()) for i, p in enumerate(self.board) if p != "." and p.upper() not in ("K",)]
        if not pieces:
            return True
        if len(pieces) == 1 and pieces[0][1] in ("B", "N"):
            return True
        if pieces and all(piece == "B" for _, piece in pieces):
            square_colors = {(square // 8 + square % 8) % 2 for square, _ in pieces}
            return len(square_colors) == 1
        return False


class ChessApp:
    LIGHT_SQUARE = "#f0d9b5"
    DARK_SQUARE = "#b58863"
    SELECTED_SQUARE = "#f6f669"
    TARGET_SQUARE = "#91c788"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Chess")
        self.root.resizable(False, False)
        self.game = ChessGame()
        self.selected: int | None = None
        self.buttons: list[tk.Button] = []

        tk.Label(root, text="Chess", font=("Segoe UI", 24, "bold")).pack(pady=(12, 4))
        self.status_label = tk.Label(root, font=("Segoe UI", 12))
        self.status_label.pack(pady=(0, 8))

        board_frame = tk.Frame(root, padx=10, pady=4)
        board_frame.pack()
        for row in range(8):
            for col in range(8):
                button = tk.Button(
                    board_frame,
                    font=("Segoe UI Symbol", 34),
                    width=2,
                    height=1,
                    relief="flat",
                    bd=0,
                    command=lambda r=row, c=col: self.on_square_click(r * 8 + c),
                )
                button.grid(row=row, column=col)
                self.buttons.append(button)

        tk.Button(root, text="New game", font=("Segoe UI", 11), command=self.new_game).pack(pady=10)
        self.refresh()

    def on_square_click(self, square: int) -> None:
        if self.selected is None:
            piece = self.game.board[square]
            if piece == "." or ChessGame._is_white(piece) != (self.game.turn == "w"):
                return
            self.selected = square
            self.refresh()
            return

        candidates = [
            move for move in self.game.legal_moves_from(self.selected) if move.end == square
        ]
        if candidates:
            move = candidates[0]
            if move.promotion:
                promotion = self.choose_promotion()
                if promotion is None:
                    return
                move = next(candidate for candidate in candidates if candidate.promotion == promotion)
            self.game.play_move(move)
            self.selected = None
            self.refresh()
            if self.game.status().startswith(("Checkmate", "Draw")):
                messagebox.showinfo("Game over", self.game.status(), parent=self.root)
        elif self.game.board[square] != "." and ChessGame._is_white(
            self.game.board[square]
        ) == (self.game.turn == "w"):
            self.selected = square
            self.refresh()
        else:
            self.selected = None
            self.refresh()

    def choose_promotion(self) -> str | None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Promote pawn")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()
        tk.Label(dialog, text="Choose a piece:", font=("Segoe UI", 11)).pack(padx=12, pady=(10, 4))
        choice = tk.StringVar(value="")
        color = "w" if self.game.turn == "w" else "b"
        for piece in PROMOTION_PIECES:
            tk.Button(
                dialog,
                text=PIECE_GLYPHS[piece if color == "w" else piece.lower()],
                font=("Segoe UI Symbol", 26),
                width=2,
                command=lambda selected=piece: (choice.set(selected), dialog.destroy()),
            ).pack(side="left", padx=4, pady=8)
        dialog.protocol(
            "WM_DELETE_WINDOW",
            lambda: (choice.set(""), dialog.destroy()),
        )
        dialog.wait_variable(choice)
        return choice.get() or None

    def new_game(self) -> None:
        self.game = ChessGame()
        self.selected = None
        self.refresh()

    def refresh(self) -> None:
        targets = {
            move.end for move in self.game.legal_moves_from(self.selected)
        } if self.selected is not None else set()
        for square, button in enumerate(self.buttons):
            row, col = divmod(square, 8)
            piece = self.game.board[square]
            button.configure(
                text=PIECE_GLYPHS.get(piece, "\u00b7" if square in targets else ""),
                bg=(
                    self.SELECTED_SQUARE if square == self.selected else
                    self.TARGET_SQUARE if square in targets else
                    self.LIGHT_SQUARE if (row + col) % 2 == 0 else self.DARK_SQUARE
                ),
                fg="#202020",
                activebackground=self.LIGHT_SQUARE if (row + col) % 2 == 0 else self.DARK_SQUARE,
            )
        self.status_label.configure(text=self.game.status())


def main() -> None:
    root = tk.Tk()
    ChessApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
