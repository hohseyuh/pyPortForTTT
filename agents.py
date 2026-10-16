# Agents for m×m tic-tac-toe.
#
#   RandomAgent      baseline, picks any legal move
#   ReflexAgent      simple reflex agent: condition-action rules (if-else) on the current percept only
#   ModelBasedAgent  model-based reflex agent: keeps an internal model of the game and runs a finite state machine
#   HumanAgent       reads moves from the keyboard

import random
from game import EMPTY, actions, player, opponent, terminal, winner, winningCells, windows


def centreOrder(board, cells):
    """Sort cells so the ones closest to the centre come first (ties broken row-major)."""
    mid = (board.m - 1) / 2
    return sorted(cells, key=lambda rc: (abs(rc[0] - mid) + abs(rc[1] - mid), rc))


def corners(board):
    e = board.m - 1
    return [(0, 0), (0, e), (e, 0), (e, e)]


class Agent:
    name = "Agent"

    def __init__(self):
        self.reason = ""

    def act(self, board):
        """Percept: the current board. Action: the (row, col) to mark."""
        raise NotImplementedError

    def observe(self, board):
        """Called with the final board when the game ends."""

    def reset(self):
        self.reason = ""


class RandomAgent(Agent):
    name = "Random"

    def __init__(self, seed=None):
        super().__init__()
        self.rng = random.Random(seed)

    def act(self, board):
        self.reason = "random legal move"
        return self.rng.choice(actions(board))


class ReflexAgent(Agent):
    """Simple reflex agent. It looks only at the current board and fires the first rule that matches."""

    name = "Reflex"

    def act(self, board):
        me = player(board)
        opp = opponent(me)
        free = set(actions(board))
        win = winningCells(board, me)
        block = winningCells(board, opp)
        mid = board.m // 2
        e = board.m - 1
        opposite = [(e - r, e - c) for r, c in corners(board)
                    if board.at(r, c) == opp and (e - r, e - c) in free]
        freeCorners = [c for c in corners(board) if c in free]

        if win:
            self.reason = "rule 1: I can complete a line, so win"
            return win[0]
        elif block:
            self.reason = "rule 2: opponent can complete a line, so block it"
            return block[0]
        elif board.m % 2 and (mid, mid) in free:
            self.reason = "rule 3: centre is free, take it"
            return (mid, mid)
        elif opposite:
            self.reason = "rule 4: opponent holds a corner, take the opposite corner"
            return opposite[0]
        elif freeCorners:
            self.reason = "rule 5: take a free corner"
            return freeCorners[0]
        else:
            self.reason = "rule 6: take any free cell"
            return min(free)


# States of the model-based agent's finite state machine
START, OPENING, BUILD, ATTACK, DEFEND, FINISH, GAME_OVER = (
    "START", "OPENING", "BUILD", "ATTACK", "DEFEND", "FINISH", "GAME_OVER")

# Events the agent derives from the percept plus its internal model, in priority order
GAME_ENDED, CAN_WIN, MUST_BLOCK, CAN_FORK, OPP_CAN_FORK, QUIET = (
    "GAME_ENDED", "CAN_WIN", "MUST_BLOCK", "CAN_FORK", "OPP_CAN_FORK", "QUIET")

ACTIVE = (START, OPENING, BUILD, ATTACK, DEFEND, FINISH)

# Transition table: (current state, event) -> next state
TRANSITIONS = {}
for _s in ACTIVE:
    TRANSITIONS[(_s, GAME_ENDED)] = GAME_OVER
    TRANSITIONS[(_s, CAN_WIN)] = FINISH
    TRANSITIONS[(_s, MUST_BLOCK)] = DEFEND
    TRANSITIONS[(_s, CAN_FORK)] = ATTACK
    TRANSITIONS[(_s, OPP_CAN_FORK)] = DEFEND
    TRANSITIONS[(_s, QUIET)] = OPENING if _s == START else BUILD
TRANSITIONS[(GAME_OVER, GAME_ENDED)] = GAME_OVER


class ModelBasedAgent(Agent):
    """Model-based reflex agent driven by a finite state machine.

    Internal model (what the reflex agent does not have):
      - the board it left after its own last move, so it can work out which move the opponent made
      - the history of both players' moves
      - a target line it has committed to and keeps building across turns, until the opponent blocks it
      - the transition model (game.result / Board.place) to predict forks one move ahead
    The current FSM state plus the event computed from the percept pick the next state, and each state
    has its own action.
    """

    name = "Model-based"

    def __init__(self):
        super().__init__()
        self.reset()

    def reset(self):
        super().reset()
        self.state = START
        self.event = None
        self.prev = None
        self.target = None
        self.myMoves, self.oppMoves = [], []
        self.trace = []

    # ---- model update -------------------------------------------------------

    def updateModel(self, board):
        """Compare the new percept with the remembered board to find the opponent's move(s)."""
        before = self.prev.cells if self.prev else (EMPTY,) * len(board.cells)
        for i, (old, new) in enumerate(zip(before, board.cells)):
            if old == EMPTY and new != EMPTY:
                self.oppMoves.append(divmod(i, board.m))

    def forkMoves(self, board, symbol):
        """Cells where symbol would get two or more ways to win at once (uses the transition model)."""
        return [c for c in centreOrder(board, actions(board))
                if len(winningCells(board.place(*c, symbol), symbol)) >= 2]

    def detectEvent(self, board):
        if terminal(board):
            return GAME_ENDED
        me = player(board)
        opp = opponent(me)
        if winningCells(board, me):
            return CAN_WIN
        if winningCells(board, opp):
            return MUST_BLOCK
        if self.forkMoves(board, me):
            return CAN_FORK
        if self.forkMoves(board, opp):
            return OPP_CAN_FORK
        return QUIET

    def step(self, board):
        self.event = self.detectEvent(board)
        self.state = TRANSITIONS[(self.state, self.event)]

    # ---- agent interface ----------------------------------------------------

    def observe(self, board):
        self.updateModel(board)
        self.prev = board
        self.step(board)
        self.trace.append((self.state, None, "game over: " + (f"{winner(board)} won" if winner(board) else "draw")))

    def act(self, board):
        self.updateModel(board)
        self.step(board)
        move = {OPENING: self.doOpening, FINISH: self.doFinish, DEFEND: self.doDefend,
                ATTACK: self.doAttack, BUILD: self.doBuild}[self.state](board)
        self.myMoves.append(move)
        self.prev = board.place(*move, player(board))
        self.trace.append((self.state, move, self.reason))
        return move

    # ---- one action per state -----------------------------------------------

    def doOpening(self, board):
        mid = board.m // 2
        if board.m % 2 and board.isEmpty(mid, mid):
            self.reason = "OPENING: take the centre"
            return (mid, mid)
        free = [c for c in corners(board) if board.isEmpty(*c)]
        self.reason = "OPENING: centre is gone, take a corner"
        return free[0] if free else centreOrder(board, actions(board))[0]

    def doFinish(self, board):
        self.reason = "FINISH: complete my line and win"
        return winningCells(board, player(board))[0]

    def doDefend(self, board):
        me = player(board)
        opp = opponent(me)
        if self.event == MUST_BLOCK:
            self.reason = "DEFEND: block the opponent's winning cell"
            return winningCells(board, opp)[0]
        # The opponent could fork next turn. Best defence: make a threat of my own that forces a block,
        # as long as that forced block does not hand the opponent a fork.
        for c in centreOrder(board, actions(board)):
            after = board.place(*c, me)
            threats = winningCells(after, me)
            if len(threats) == 1 and len(winningCells(after.place(*threats[0], opp), opp)) < 2:
                self.reason = "DEFEND: force the opponent to block instead of forking"
                return c
        self.reason = "DEFEND: occupy the opponent's fork cell"
        return self.forkMoves(board, opp)[0]

    def doAttack(self, board):
        self.reason = "ATTACK: create two threats at once (fork)"
        return self.forkMoves(board, player(board))[0]

    def doBuild(self, board):
        me = player(board)
        opp = opponent(me)

        def openForMe(w):
            return all(board.at(r, c) != opp for r, c in w) and any(board.isEmpty(r, c) for r, c in w)

        if self.target and openForMe(self.target):
            self.reason = "BUILD: keep extending my remembered target line"
        else:
            wasBlocked = self.target is not None
            mid = (board.m - 1) / 2
            candidates = [w for w in windows(board.m, board.k) if openForMe(w)]
            if candidates:
                self.target = max(candidates, key=lambda w: (
                    sum(board.at(r, c) == me for r, c in w),
                    -sum(abs(r - mid) + abs(c - mid) for r, c in w)))
                self.reason = ("BUILD: opponent blocked my line, pick a new target line" if wasBlocked
                               else "BUILD: pick the most promising open line as my target")
            else:
                self.target = None

        if self.target:
            return centreOrder(board, [c for c in self.target if board.isEmpty(*c)])[0]

        # No line is winnable for me any more: take the free cell that lies on the most lines.
        self.reason = "BUILD: no winnable line left, take the free cell on the most lines"
        return max(centreOrder(board, actions(board)),
                   key=lambda cell: sum(cell in w for w in windows(board.m, board.k)))


class HumanAgent(Agent):
    name = "Human"

    def act(self, board):
        free = set(actions(board))
        while True:
            raw = input(f"  {player(board)} move as 'row col': ").replace(",", " ").split()
            try:
                move = (int(raw[0]), int(raw[1]))
            except (ValueError, IndexError):
                print("  type two numbers, e.g. 1 2")
                continue
            if move in free:
                self.reason = "human choice"
                return move
            print("  that cell is taken or off the board")


AGENTS = {"random": RandomAgent, "reflex": ReflexAgent, "model": ModelBasedAgent, "human": HumanAgent}
