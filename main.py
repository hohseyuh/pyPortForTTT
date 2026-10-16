# Tic-tac-toe agents: demo, interactive play and agent-vs-agent matches.
#
#   python main.py                                  # demo (same as: python main.py demo)
#   python main.py play --x human --o model         # play against the model-based agent
#   python main.py play --x reflex --o model -m 4 -k 3
#   python main.py match reflex model -n 200        # many games, sides swapped every game

import argparse
from game import Board, initialState, player, result, terminal, winner
from agents import AGENTS, RandomAgent, ReflexAgent, ModelBasedAgent, START

SCENARIOS = [
    ("Empty board, X to move", ["...", "...", "..."]),
    ("X can win in one move", ["XX.", "OO.", "..."]),
    ("O threatens the middle row, X must block", ["X..", "OO.", "X.."]),
    ("X can fork (two threats at once)", ["XO.", ".X.", "..O"]),
    ("Fork trap: O to move, X holds opposite corners", ["X..", ".O.", "..X"]),
]


def playGame(xAgent, oAgent, m=3, k=3, verbose=False, showTrace=False):
    """Play one game and return 'X', 'O' or None for a draw."""
    agents = {"X": xAgent, "O": oAgent}
    for a in agents.values():
        a.reset()
    board = initialState(m, k)
    if verbose:
        print(board, "\n")
    while not terminal(board):
        side = player(board)
        move = agents[side].act(board)
        board = result(board, move)
        if verbose:
            print(f"{side} ({agents[side].name}) plays {move}: {agents[side].reason}\n{board}\n")
    for a in agents.values():
        a.observe(board)
    w = winner(board)
    if verbose:
        print(f"Result: {w + ' wins' if w else 'draw'}\n")
    if showTrace:
        for side, a in agents.items():
            if isinstance(a, ModelBasedAgent):
                print(f"FSM trace of {side} ({a.name}):")
                print("  " + " -> ".join([START] + [s for s, _, _ in a.trace]) + "\n")
    return w


def match(nameA, nameB, games=100, m=3, k=3, seed=42):
    """Play games between two agent types, swapping sides each game. Returns a tally.
    The random agent is seeded so the results are reproducible."""
    def make(name):
        return RandomAgent(seed) if name == "random" else AGENTS[name]()
    a, b = make(nameA), make(nameB)
    tally = {a.name: 0, b.name: 0, "draw": 0}
    for g in range(games):
        x, o = (a, b) if g % 2 == 0 else (b, a)
        w = playGame(x, o, m, k)
        tally[{"X": x.name, "O": o.name}.get(w, "draw")] += 1
    return tally


def demo():
    print("=" * 60)
    print("1. How each agent reacts to the same situations")
    print("=" * 60)
    for title, rows in SCENARIOS:
        board = Board.fromRows(rows)
        print(f"\n{title}  ({player(board)} to move)\n{board}\n")
        for agent in (ReflexAgent(), ModelBasedAgent()):
            move = agent.act(board)
            state = f" [state {agent.state}]" if isinstance(agent, ModelBasedAgent) else ""
            print(f"  {agent.name:<12} -> {move}{state}  {agent.reason}")

    print("\n" + "=" * 60)
    print("2. Full game: Reflex (X) vs Model-based (O)")
    print("=" * 60 + "\n")
    playGame(ReflexAgent(), ModelBasedAgent(), verbose=True, showTrace=True)

    print("=" * 60)
    print("3. Matches, 3x3, 200 games each, sides swapped every game")
    print("=" * 60)
    for a, b in (("reflex", "random"), ("model", "random"), ("model", "reflex")):
        t = match(a, b, 200)
        print("  " + ",  ".join(f"{k}: {v}" for k, v in t.items()))

    print("\n4. Larger board, 5x5 with 4 in a row, 100 games")
    for a, b in (("model", "random"), ("model", "reflex")):
        t = match(a, b, 100, 5, 4)
        print("  " + ",  ".join(f"{k}: {v}" for k, v in t.items()))


def main():
    p = argparse.ArgumentParser(description="Tic-tac-toe with a reflex agent and a model-based agent.")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("demo", help="run the demo (default)")
    pl = sub.add_parser("play", help="play one game")
    pl.add_argument("--x", choices=AGENTS, default="human")
    pl.add_argument("--o", choices=AGENTS, default="model")
    mt = sub.add_parser("match", help="play many games between two agents")
    mt.add_argument("a", choices=[n for n in AGENTS if n != "human"])
    mt.add_argument("b", choices=[n for n in AGENTS if n != "human"])
    mt.add_argument("-n", type=int, default=100, help="number of games (default 100)")
    for sp in (pl, mt):
        sp.add_argument("-m", type=int, default=3, help="board size (default 3)")
        sp.add_argument("-k", type=int, default=3, help="marks in a row to win (default 3)")
    args = p.parse_args()

    if args.cmd == "play":
        playGame(AGENTS[args.x](), AGENTS[args.o](), args.m, args.k, verbose=True, showTrace=True)
    elif args.cmd == "match":
        t = match(args.a, args.b, args.n, args.m, args.k)
        print(",  ".join(f"{k}: {v}" for k, v in t.items()))
    else:
        demo()


if __name__ == "__main__":
    main()
