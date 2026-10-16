# Run with: python -m unittest -v

import copy
import unittest
from game import Board, initialState, player, actions, result, winner, terminal, utility, winningCells, windows
from agents import (ReflexAgent, ModelBasedAgent, RandomAgent, TRANSITIONS, START, OPENING, BUILD, ATTACK, DEFEND,
                    FINISH, GAME_OVER, CAN_WIN, MUST_BLOCK, CAN_FORK, OPP_CAN_FORK, QUIET, GAME_ENDED)
from main import playGame, match


def outcomes(agent, side, board=None):
    """Play the agent against every possible sequence of opponent moves. Returns (wins, draws, losses)."""
    board = board or initialState()
    if terminal(board):
        u = utility(board)
        if u == 0:
            return 0, 1, 0
        return (1, 0, 0) if (u == 1) == (side == "X") else (0, 0, 1)
    if player(board) == side:
        return outcomes(agent, side, result(board, agent.act(board)))
    total = (0, 0, 0)
    for a in actions(board):
        sub = outcomes(copy.deepcopy(agent), side, result(board, a))
        total = tuple(x + y for x, y in zip(total, sub))
    return total


class TestRules(unittest.TestCase):
    def testXMovesFirstAndTurnsAlternate(self):
        b = initialState()
        self.assertEqual(player(b), "X")
        self.assertEqual(player(result(b, (0, 0))), "O")

    def testIllegalMovesRaise(self):
        b = result(initialState(), (0, 0))
        with self.assertRaises(ValueError):
            result(b, (0, 0))
        with self.assertRaises(ValueError):
            result(b, (3, 0))

    def testWinnerInEveryDirection(self):
        self.assertEqual(winner(Board.fromRows(["XXX", "OO.", "..."])), "X")
        self.assertEqual(winner(Board.fromRows(["OX.", "OX.", "O.X"])), "O")
        self.assertEqual(winner(Board.fromRows(["X.O", ".XO", "..X"])), "X")
        self.assertEqual(winner(Board.fromRows(["X.O", "XO.", "O.X"])), "O")

    def testDrawAndUtility(self):
        draw = Board.fromRows(["XOX", "XOO", "OXX"])
        self.assertTrue(terminal(draw))
        self.assertEqual(utility(draw), 0)
        self.assertIsNone(utility(initialState()))

    def testKSmallerThanM(self):
        b = Board.fromRows(["....", ".XX.", "....", "...."], k=3)
        self.assertEqual(winningCells(b, "X"), [(1, 0), (1, 3)])
        self.assertEqual(len(windows(4, 3)), 24)


class TestReflexAgent(unittest.TestCase):
    def check(self, rows, move, rule):
        agent = ReflexAgent()
        self.assertEqual(agent.act(Board.fromRows(rows)), move)
        self.assertIn(rule, agent.reason)

    def testRuleWin(self):
        self.check(["XX.", "OO.", "..."], (0, 2), "rule 1")

    def testRuleBlock(self):
        self.check(["X..", "OO.", "X.."], (1, 2), "rule 2")

    def testWinBeatsBlock(self):
        self.check(["XX.", "OO.", "O.X"], (0, 2), "rule 1")

    def testRuleCentre(self):
        self.check(["...", "...", "..."], (1, 1), "rule 3")

    def testRuleOppositeCorner(self):
        self.check(["O..", ".X.", "..."], (2, 2), "rule 4")

    def testRuleFreeCorner(self):
        self.check(["...", ".O.", "..."], (0, 0), "rule 5")

    def testReflexFallsForTheForkTrap(self):
        # A simple reflex agent has no look-ahead, so some opponent lines beat it.
        self.assertGreater(outcomes(ReflexAgent(), "O")[2], 0)


class TestModelBasedAgent(unittest.TestCase):
    def testTransitionTableCoversEveryActiveState(self):
        for s in (START, OPENING, BUILD, ATTACK, DEFEND, FINISH):
            for e in (GAME_ENDED, CAN_WIN, MUST_BLOCK, CAN_FORK, OPP_CAN_FORK, QUIET):
                self.assertIn((s, e), TRANSITIONS)
        self.assertEqual(TRANSITIONS[(START, QUIET)], OPENING)
        self.assertEqual(TRANSITIONS[(OPENING, QUIET)], BUILD)
        self.assertEqual(TRANSITIONS[(BUILD, MUST_BLOCK)], DEFEND)

    def testStatesForScenarios(self):
        cases = [(["...", "...", "..."], OPENING, (1, 1)),
                 (["XX.", "OO.", "..."], FINISH, (0, 2)),
                 (["X..", "OO.", "X.."], DEFEND, (1, 2)),
                 (["XO.", ".X.", "..O"], ATTACK, (1, 0))]
        for rows, state, move in cases:
            agent = ModelBasedAgent()
            self.assertEqual(agent.act(Board.fromRows(rows)), move)
            self.assertEqual(agent.state, state)

    def testAvoidsTheForkTrap(self):
        agent = ModelBasedAgent()
        move = agent.act(Board.fromRows(["X..", ".O.", "..X"]))
        self.assertEqual(agent.state, DEFEND)
        self.assertNotIn(move, [(0, 2), (2, 0)])   # a corner here loses

    def testModelTracksOpponentMoves(self):
        agent = ModelBasedAgent()
        b = result(initialState(), (0, 0))         # X (opponent) plays a corner
        b = result(b, agent.act(b))                 # agent answers
        b = result(b, (2, 2))                       # X plays the opposite corner
        agent.act(b)
        self.assertEqual(agent.oppMoves, [(0, 0), (2, 2)])
        self.assertEqual(len(agent.myMoves), 2)

    def testKeepsTargetLineBetweenTurns(self):
        agent = ModelBasedAgent()
        b = initialState(5, 5)
        b = result(b, agent.act(b))                 # opening, centre
        b = result(b, (0, 0))
        b = result(b, agent.act(b))                 # picks a target line
        target = agent.target
        b = result(b, (4, 4))
        agent.act(b)
        self.assertEqual(agent.state, BUILD)
        self.assertEqual(agent.target, target)
        self.assertIn("keep extending", agent.reason)

    def testGameOverState(self):
        agent = ModelBasedAgent()
        playGame(agent, RandomAgent(seed=1))
        self.assertEqual(agent.state, GAME_OVER)

    def testNeverLosesAsX(self):
        self.assertEqual(outcomes(ModelBasedAgent(), "X")[2], 0)

    def testNeverLosesAsO(self):
        self.assertEqual(outcomes(ModelBasedAgent(), "O")[2], 0)


class TestDemo(unittest.TestCase):
    def testModelBeatsOrDrawsReflex(self):
        t = match("model", "reflex", 20)
        self.assertEqual(t["Reflex"], 0)

    def testBiggerBoardsRun(self):
        for m, k in ((4, 3), (5, 4), (6, 4)):
            w = playGame(ModelBasedAgent(), RandomAgent(seed=m), m, k)
            self.assertIn(w, ("X", "O", None))


if __name__ == "__main__":
    unittest.main()
