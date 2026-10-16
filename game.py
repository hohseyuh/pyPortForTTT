# Generalised m×m tic-tac-toe with k-in-a-row, ported from the C++ engine (Board, Rules, KDetector).
#
# Rules follow the AIMA game interface: initialState, player, actions, result, winner, terminal, utility.

from functools import lru_cache

EMPTY = " "


class Board:
    """Immutable m×m board. Cells are stored row-major in a tuple of 'X', 'O' or ' '."""

    __slots__ = ("m", "k", "cells")

    def __init__(self, m=3, k=3, cells=None):
        if m < 1 or not 1 <= k <= m:
            raise ValueError("need m >= 1 and 1 <= k <= m")
        self.m, self.k = m, k
        self.cells = tuple(cells) if cells is not None else (EMPTY,) * (m * m)

    @classmethod
    def fromRows(cls, rows, k=None):
        """Board from strings such as ["X O", " X ", "  O"]. '.' and '_' also mean empty."""
        m = len(rows)
        cells = [EMPTY if ch in "._" else ch for row in rows for ch in row.ljust(m)]
        return cls(m, k or m, cells)

    def at(self, r, c):
        return self.cells[r * self.m + c]

    def inBounds(self, r, c):
        return 0 <= r < self.m and 0 <= c < self.m

    def isEmpty(self, r, c):
        return self.at(r, c) == EMPTY

    def countEmpty(self):
        return self.cells.count(EMPTY)

    def place(self, r, c, symbol):
        cells = list(self.cells)
        cells[r * self.m + c] = symbol
        return Board(self.m, self.k, cells)

    def __eq__(self, other):
        return isinstance(other, Board) and (self.m, self.k, self.cells) == (other.m, other.k, other.cells)

    def __hash__(self):
        return hash((self.m, self.k, self.cells))

    def __str__(self):
        head = "    " + "   ".join(str(c) for c in range(self.m))
        sep = "   " + "+".join("---" for _ in range(self.m))
        rows = [f" {r}  " + " | ".join(self.at(r, c) for c in range(self.m)) for r in range(self.m)]
        return "\n".join([head] + [x for pair in zip(rows, [sep] * self.m) for x in pair][:-1])


@lru_cache(maxsize=None)
def windows(m, k):
    """Every run of k cells in a row, column, diagonal or anti-diagonal, as tuples of (r, c)."""
    out = []
    for r in range(m):
        for c in range(m):
            for dr, dc in ((0, 1), (1, 0), (1, 1), (1, -1)):
                endR, endC = r + dr * (k - 1), c + dc * (k - 1)
                if 0 <= endR < m and 0 <= endC < m:
                    out.append(tuple((r + dr * i, c + dc * i) for i in range(k)))
    return tuple(out)


def initialState(m=3, k=3):
    return Board(m, k)


def player(board):
    """X moves first, so X is to move whenever the counts are equal."""
    return "X" if board.cells.count("X") == board.cells.count("O") else "O"


def opponent(symbol):
    return "O" if symbol == "X" else "X"


def actions(board):
    """Empty cells in row-major order."""
    return [(r, c) for r in range(board.m) for c in range(board.m) if board.isEmpty(r, c)]


def result(board, action):
    r, c = action
    if not board.inBounds(r, c):
        raise ValueError(f"action {action} is out of bounds")
    if not board.isEmpty(r, c):
        raise ValueError(f"cell {action} is not empty")
    return board.place(r, c, player(board))


def winner(board):
    for w in windows(board.m, board.k):
        first = board.at(*w[0])
        if first != EMPTY and all(board.at(r, c) == first for r, c in w):
            return first
    return None


def terminal(board):
    return winner(board) is not None or board.countEmpty() == 0


def utility(board):
    """+1 if X won, -1 if O won, 0 for a draw, None while the game is still running."""
    w = winner(board)
    if w:
        return 1 if w == "X" else -1
    return 0 if board.countEmpty() == 0 else None


def winningCells(board, symbol):
    """Empty cells that would complete k-in-a-row for symbol right now."""
    cells = set()
    for w in windows(board.m, board.k):
        marks = [board.at(r, c) for r, c in w]
        if marks.count(symbol) == board.k - 1 and marks.count(EMPTY) == 1:
            cells.add(w[marks.index(EMPTY)])
    return sorted(cells)
