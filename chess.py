from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple

FILES = "abcdefgh"
RANKS = "12345678"

WHITE = "w"
BLACK = "b"

PIECE_VALUES = {
    "P": 100, "N": 320, "B": 330, "R": 500, "Q": 900, "K": 0,
    "p": -100, "n": -320, "b": -330, "r": -500, "q": -900, "k": 0,
    ".": 0,
}


@dataclass(frozen=True)
class Move:
    from_row: int
    from_col: int
    to_row: int
    to_col: int
    promotion: Optional[str] = None
    is_en_passant: bool = False
    is_castling: bool = False

    def to_uci(self) -> str:
        s = (
            square_name(self.from_row, self.from_col)
            + square_name(self.to_row, self.to_col)
        )
        if self.promotion:
            s += self.promotion.lower()
        return s


class Board:
    def __init__(self, fen: Optional[str] = None):
        if fen is None:
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        self.load_fen(fen)

    def load_fen(self, fen: str) -> None:
        parts = fen.split()
        if len(parts) < 4:
            raise ValueError("Invalid FEN")

        placement, active, castling, en_passant = parts[:4]
        self.halfmove_clock = int(parts[4]) if len(parts) > 4 else 0
        self.fullmove_number = int(parts[5]) if len(parts) > 5 else 1

        rows = placement.split("/")
        if len(rows) != 8:
            raise ValueError("Invalid FEN board rows")

        self.board: List[List[str]] = []
        for row in rows:
            current = []
            for ch in row:
                if ch.isdigit():
                    current.extend(["."] * int(ch))
                else:
                    current.append(ch)
            if len(current) != 8:
                raise ValueError("Invalid FEN row width")
            self.board.append(current)

        self.side_to_move = active
        self.castling_rights = castling if castling != "-" else ""
        self.en_passant = None if en_passant == "-" else parse_square(en_passant)

    def copy(self) -> "Board":
        b = Board(self.to_fen())
        return b

    def to_fen(self) -> str:
        rows = []
        for r in range(8):
            empty = 0
            fen_row = ""
            for c in range(8):
                piece = self.board[r][c]
                if piece == ".":
                    empty += 1
                else:
                    if empty:
                        fen_row += str(empty)
                        empty = 0
                    fen_row += piece
            if empty:
                fen_row += str(empty)
            rows.append(fen_row)

        castling = self.castling_rights if self.castling_rights else "-"
        en_passant = "-" if self.en_passant is None else square_name(*self.en_passant)
        return (
            "/".join(rows)
            + f" {self.side_to_move} {castling} {en_passant} "
            + f"{self.halfmove_clock} {self.fullmove_number}"
        )

    def print_board(self) -> None:
        print()
        for r in range(8):
            print(8 - r, end="  ")
            for c in range(8):
                print(self.board[r][c], end=" ")
            print()
        print()
        print("   a b c d e f g h")
        print()
        print(f"Turn: {'White' if self.side_to_move == WHITE else 'Black'}")
        print(f"FEN : {self.to_fen()}")
        print()

    def piece_at(self, row: int, col: int) -> str:
        return self.board[row][col]

    def set_piece(self, row: int, col: int, piece: str) -> None:
        self.board[row][col] = piece

    def is_white_piece(self, piece: str) -> bool:
        return piece.isupper()

    def is_black_piece(self, piece: str) -> bool:
        return piece.islower()

    def same_color(self, piece: str, color: str) -> bool:
        return (color == WHITE and piece.isupper()) or (color == BLACK and piece.islower())

    def enemy_color(self, color: str) -> str:
        return BLACK if color == WHITE else WHITE

    def king_position(self, color: str) -> Tuple[int, int]:
        target = "K" if color == WHITE else "k"
        for r in range(8):
            for c in range(8):
                if self.board[r][c] == target:
                    return r, c
        raise ValueError("King not found")

    def is_in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < 8 and 0 <= col < 8

    def is_square_attacked(self, row: int, col: int, by_color: str) -> bool:
        # Pawns
        if by_color == WHITE:
            pawn_sources = [(row + 1, col - 1), (row + 1, col + 1)]
            for rr, cc in pawn_sources:
                if self.is_in_bounds(rr, cc) and self.board[rr][cc] == "P":
                    return True
        else:
            pawn_sources = [(row - 1, col - 1), (row - 1, col + 1)]
            for rr, cc in pawn_sources:
                if self.is_in_bounds(rr, cc) and self.board[rr][cc] == "p":
                    return True

        # Knights
        knight_offsets = [
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1),
        ]
        knight = "N" if by_color == WHITE else "n"
        for dr, dc in knight_offsets:
            rr, cc = row + dr, col + dc
            if self.is_in_bounds(rr, cc) and self.board[rr][cc] == knight:
                return True

        # Bishops / Queens diagonals
        diag_pieces = {"B", "Q"} if by_color == WHITE else {"b", "q"}
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            rr, cc = row + dr, col + dc
            while self.is_in_bounds(rr, cc):
                piece = self.board[rr][cc]
                if piece != ".":
                    if piece in diag_pieces:
                        return True
                    break
                rr += dr
                cc += dc

        # Rooks / Queens straight
        line_pieces = {"R", "Q"} if by_color == WHITE else {"r", "q"}
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            rr, cc = row + dr, col + dc
            while self.is_in_bounds(rr, cc):
                piece = self.board[rr][cc]
                if piece != ".":
                    if piece in line_pieces:
                        return True
                    break
                rr += dr
                cc += dc

        # Kings
        king = "K" if by_color == WHITE else "k"
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                rr, cc = row + dr, col + dc
                if self.is_in_bounds(rr, cc) and self.board[rr][cc] == king:
                    return True

        return False

    def in_check(self, color: str) -> bool:
        kr, kc = self.king_position(color)
        return self.is_square_attacked(kr, kc, self.enemy_color(color))

    def generate_pseudo_legal_moves(self, color: str) -> List[Move]:
        moves: List[Move] = []

        for r in range(8):
            for c in range(8):
                piece = self.board[r][c]
                if piece == "." or not self.same_color(piece, color):
                    continue

                p = piece.lower()

                if p == "p":
                    moves.extend(self._pawn_moves(r, c, color))
                elif p == "n":
                    moves.extend(self._knight_moves(r, c, color))
                elif p == "b":
                    moves.extend(self._slider_moves(r, c, color, [(-1, -1), (-1, 1), (1, -1), (1, 1)]))
                elif p == "r":
                    moves.extend(self._slider_moves(r, c, color, [(-1, 0), (1, 0), (0, -1), (0, 1)]))
                elif p == "q":
                    moves.extend(self._slider_moves(
                        r, c, color,
                        [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)]
                    ))
                elif p == "k":
                    moves.extend(self._king_moves(r, c, color))

        return moves

    def legal_moves(self, color: Optional[str] = None) -> List[Move]:
        if color is None:
            color = self.side_to_move

        legal: List[Move] = []
        for move in self.generate_pseudo_legal_moves(color):
            new_board = self.make_move(move)
            if not new_board.in_check(color):
                legal.append(move)
        return legal

    def _pawn_moves(self, r: int, c: int, color: str) -> List[Move]:
        moves = []
        direction = -1 if color == WHITE else 1
        start_row = 6 if color == WHITE else 1
        promotion_row = 0 if color == WHITE else 7
        enemy = self.enemy_color(color)

        # Forward one
        nr = r + direction
        if self.is_in_bounds(nr, c) and self.board[nr][c] == ".":
            if nr == promotion_row:
                for promo in "qrbn":
                    moves.append(Move(r, c, nr, c, promotion=promo))
            else:
                moves.append(Move(r, c, nr, c))

            # Forward two
            nr2 = r + 2 * direction
            if r == start_row and self.board[nr2][c] == ".":
                moves.append(Move(r, c, nr2, c))

        # Captures
        for dc in (-1, 1):
            nc = c + dc
            nr = r + direction
            if not self.is_in_bounds(nr, nc):
                continue

            target = self.board[nr][nc]
            if target != "." and self.same_color(target, enemy):
                if nr == promotion_row:
                    for promo in "qrbn":
                        moves.append(Move(r, c, nr, nc, promotion=promo))
                else:
                    moves.append(Move(r, c, nr, nc))

        # En passant
        if self.en_passant is not None:
            ep_r, ep_c = self.en_passant
            if ep_r == r + direction and abs(ep_c - c) == 1:
                moves.append(Move(r, c, ep_r, ep_c, is_en_passant=True))

        return moves

    def _knight_moves(self, r: int, c: int, color: str) -> List[Move]:
        moves = []
        for dr, dc in [
            (-2, -1), (-2, 1), (-1, -2), (-1, 2),
            (1, -2), (1, 2), (2, -1), (2, 1),
        ]:
            nr, nc = r + dr, c + dc
            if not self.is_in_bounds(nr, nc):
                continue
            target = self.board[nr][nc]
            if target == "." or not self.same_color(target, color):
                moves.append(Move(r, c, nr, nc))
        return moves

    def _slider_moves(self, r: int, c: int, color: str, directions: List[Tuple[int, int]]) -> List[Move]:
        moves = []
        for dr, dc in directions:
            nr, nc = r + dr, c + dc
            while self.is_in_bounds(nr, nc):
                target = self.board[nr][nc]
                if target == ".":
                    moves.append(Move(r, c, nr, nc))
                else:
                    if not self.same_color(target, color):
                        moves.append(Move(r, c, nr, nc))
                    break
                nr += dr
                nc += dc
        return moves

    def _king_moves(self, r: int, c: int, color: str) -> List[Move]:
        moves = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if not self.is_in_bounds(nr, nc):
                    continue
                target = self.board[nr][nc]
                if target == "." or not self.same_color(target, color):
                    moves.append(Move(r, c, nr, nc))

        # Castling
        if color == WHITE and (r, c) == (7, 4):
            if "K" in self.castling_rights:
                if (
                    self.board[7][5] == "." and self.board[7][6] == "."
                    and not self.in_check(WHITE)
                    and not self.is_square_attacked(7, 5, BLACK)
                    and not self.is_square_attacked(7, 6, BLACK)
                    and self.board[7][7] == "R"
                ):
                    moves.append(Move(7, 4, 7, 6, is_castling=True))
            if "Q" in self.castling_rights:
                if (
                    self.board[7][1] == "." and self.board[7][2] == "." and self.board[7][3] == "."
                    and not self.in_check(WHITE)
                    and not self.is_square_attacked(7, 3, BLACK)
                    and not self.is_square_attacked(7, 2, BLACK)
                    and self.board[7][0] == "R"
                ):
                    moves.append(Move(7, 4, 7, 2, is_castling=True))

        if color == BLACK and (r, c) == (0, 4):
            if "k" in self.castling_rights:
                if (
                    self.board[0][5] == "." and self.board[0][6] == "."
                    and not self.in_check(BLACK)
                    and not self.is_square_attacked(0, 5, WHITE)
                    and not self.is_square_attacked(0, 6, WHITE)
                    and self.board[0][7] == "r"
                ):
                    moves.append(Move(0, 4, 0, 6, is_castling=True))
            if "q" in self.castling_rights:
                if (
                    self.board[0][1] == "." and self.board[0][2] == "." and self.board[0][3] == "."
                    and not self.in_check(BLACK)
                    and not self.is_square_attacked(0, 3, WHITE)
                    and not self.is_square_attacked(0, 2, WHITE)
                    and self.board[0][0] == "r"
                ):
                    moves.append(Move(0, 4, 0, 2, is_castling=True))

        return moves

    def make_move(self, move: Move) -> "Board":
        new_board = self.copy()

        piece = new_board.board[move.from_row][move.from_col]
        target = new_board.board[move.to_row][move.to_col]

        # Reset en passant by default
        new_board.en_passant = None

        # Halfmove clock
        if piece.lower() == "p" or target != "." or move.is_en_passant:
            new_board.halfmove_clock = 0
        else:
            new_board.halfmove_clock += 1

        # Move piece
        new_board.board[move.from_row][move.from_col] = "."

        # En passant capture
        if move.is_en_passant:
            capture_row = move.to_row + 1 if piece.isupper() else move.to_row - 1
            new_board.board[capture_row][move.to_col] = "."

        # Castling rook movement
        if move.is_castling:
            if piece == "K" and move.to_col == 6:
                new_board.board[7][5] = "R"
                new_board.board[7][7] = "."
            elif piece == "K" and move.to_col == 2:
                new_board.board[7][3] = "R"
                new_board.board[7][0] = "."
            elif piece == "k" and move.to_col == 6:
                new_board.board[0][5] = "r"
                new_board.board[0][7] = "."
            elif piece == "k" and move.to_col == 2:
                new_board.board[0][3] = "r"
                new_board.board[0][0] = "."

        # Promotion
        if move.promotion and piece.lower() == "p":
            promoted = move.promotion.upper() if piece.isupper() else move.promotion.lower()
            new_board.board[move.to_row][move.to_col] = promoted
        else:
            new_board.board[move.to_row][move.to_col] = piece

        # Set en passant square after a double pawn push
        if piece.lower() == "p" and abs(move.to_row - move.from_row) == 2:
            ep_row = (move.from_row + move.to_row) // 2
            new_board.en_passant = (ep_row, move.from_col)

        # Update castling rights on king move
        if piece == "K":
            new_board.castling_rights = new_board.castling_rights.replace("K", "").replace("Q", "")
        elif piece == "k":
            new_board.castling_rights = new_board.castling_rights.replace("k", "").replace("q", "")

        # Update castling rights on rook move
        if piece == "R":
            if (move.from_row, move.from_col) == (7, 0):
                new_board.castling_rights = new_board.castling_rights.replace("Q", "")
            elif (move.from_row, move.from_col) == (7, 7):
                new_board.castling_rights = new_board.castling_rights.replace("K", "")
        elif piece == "r":
            if (move.from_row, move.from_col) == (0, 0):
                new_board.castling_rights = new_board.castling_rights.replace("q", "")
            elif (move.from_row, move.from_col) == (0, 7):
                new_board.castling_rights = new_board.castling_rights.replace("k", "")

        # Update castling rights on rook capture
        if target == "R":
            if (move.to_row, move.to_col) == (7, 0):
                new_board.castling_rights = new_board.castling_rights.replace("Q", "")
            elif (move.to_row, move.to_col) == (7, 7):
                new_board.castling_rights = new_board.castling_rights.replace("K", "")
        elif target == "r":
            if (move.to_row, move.to_col) == (0, 0):
                new_board.castling_rights = new_board.castling_rights.replace("q", "")
            elif (move.to_row, move.to_col) == (0, 7):
                new_board.castling_rights = new_board.castling_rights.replace("k", "")

        # Switch turn
        new_board.side_to_move = BLACK if self.side_to_move == WHITE else WHITE

        # Fullmove number increments after Black moves
        if self.side_to_move == BLACK:
            new_board.fullmove_number += 1

        return new_board

    def game_status(self) -> str:
        moves = self.legal_moves(self.side_to_move)
        if moves:
            if self.in_check(self.side_to_move):
                return "check"
            return "ongoing"

        if self.in_check(self.side_to_move):
            return "checkmate"
        return "stalemate"

    def evaluate(self) -> int:
        score = 0
        for r in range(8):
            for c in range(8):
                score += PIECE_VALUES[self.board[r][c]]

        # Slight mobility bonus
        current = len(self.legal_moves(self.side_to_move))
        other = len(self.legal_moves(self.enemy_color(self.side_to_move)))
        mobility_bonus = 2 * (current - other)

        # Score from White's perspective
        if self.side_to_move == WHITE:
            score += mobility_bonus
        else:
            score -= mobility_bonus

        return score


def square_name(row: int, col: int) -> str:
    return FILES[col] + str(8 - row)


def parse_square(s: str) -> Tuple[int, int]:
    if len(s) != 2 or s[0] not in FILES or s[1] not in RANKS:
        raise ValueError(f"Invalid square: {s}")
    col = FILES.index(s[0])
    row = 8 - int(s[1])
    return row, col


def parse_uci_move(text: str, board: Board) -> Optional[Move]:
    text = text.strip().lower()
    if len(text) not in (4, 5):
        return None

    try:
        from_row, from_col = parse_square(text[:2])
        to_row, to_col = parse_square(text[2:4])
    except ValueError:
        return None

    promotion = text[4] if len(text) == 5 else None

    legal = board.legal_moves()
    for move in legal:
        if (
            move.from_row == from_row
            and move.from_col == from_col
            and move.to_row == to_row
            and move.to_col == to_col
            and (move.promotion == promotion or (move.promotion is None and promotion is None))
        ):
            return move
    return None


def minimax(board: Board, depth: int, alpha: int, beta: int, maximizing: bool) -> Tuple[int, Optional[Move]]:
    status = board.game_status()

    if status == "checkmate":
        if board.side_to_move == WHITE:
            return -100000, None
        return 100000, None

    if status == "stalemate":
        return 0, None

    if depth == 0:
        return board.evaluate(), None

    legal = board.legal_moves()
    best_move = None

    if maximizing:
        max_eval = -10**9
        for move in legal:
            score, _ = minimax(board.make_move(move), depth - 1, alpha, beta, False)
            if score > max_eval:
                max_eval = score
                best_move = move
            alpha = max(alpha, score)
            if beta <= alpha:
                break
        return max_eval, best_move

    min_eval = 10**9
    for move in legal:
        score, _ = minimax(board.make_move(move), depth - 1, alpha, beta, True)
        if score < min_eval:
            min_eval = score
            best_move = move
        beta = min(beta, score)
        if beta <= alpha:
            break
    return min_eval, best_move


def engine_best_move(board: Board, depth: int = 3) -> Optional[Move]:
    maximizing = board.side_to_move == WHITE
    _, move = minimax(board, depth, -10**9, 10**9, maximizing)
    return move


def main():
    print("Simple Python Chess Engine")
    print("Enter moves in UCI format, e.g. e2e4 or e7e8q")
    print("Commands: moves, fen, ai, quit")
    print()

    board = Board()

    while True:
        board.print_board()

        status = board.game_status()
        if status == "checkmate":
            winner = "Black" if board.side_to_move == WHITE else "White"
            print(f"Checkmate. {winner} wins.")
            break
        elif status == "stalemate":
            print("Stalemate.")
            break
        elif status == "check":
            print("Check!")

        user_input = input("> ").strip().lower()

        if user_input == "quit":
            break
        elif user_input == "fen":
            print(board.to_fen())
            continue
        elif user_input == "moves":
            legal = board.legal_moves()
            print("Legal moves:")
            print(" ".join(m.to_uci() for m in legal))
            print()
            continue
        elif user_input.startswith("loadfen "):
            fen = user_input[len("loadfen "):].strip()
            try:
                board = Board(fen)
            except Exception as e:
                print(f"Invalid FEN: {e}")
            continue
        elif user_input.startswith("ai"):
            parts = user_input.split()
            depth = 3
            if len(parts) == 2 and parts[1].isdigit():
                depth = int(parts[1])

            move = engine_best_move(board, depth=depth)
            if move is None:
                print("No legal move available.")
            else:
                print(f"Engine plays: {move.to_uci()}")
                board = board.make_move(move)
            continue

        move = parse_uci_move(user_input, board)
        if move is None:
            print("Invalid or illegal move.")
            continue

        board = board.make_move(move)


if __name__ == "__main__":
    main()