# Draws the agent diagrams as SVG files (no dependencies).
#
#   python diagrams.py            # writes diagrams/reflex_flow.svg, diagrams/fsm.svg, diagrams/model_agent.svg

import math, os

FONT = 'font-family="Helvetica, Arial, sans-serif"'
INK, MUTED, LINE = "#111827", "#4b5563", "#6b7280"
COLOURS = {  # fill, stroke
    "START": ("#eff6ff", "#2563eb"), "OPENING": ("#f5f3ff", "#7c3aed"), "BUILD": ("#f9fafb", "#4b5563"),
    "DEFEND": ("#fff7ed", "#ea580c"), "ATTACK": ("#fef2f2", "#dc2626"), "FINISH": ("#f0fdf4", "#16a34a"),
    "GAME_OVER": ("#f3f4f6", "#111827"),
}


def svg(width, height, body, title, subtitle=""):
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" {FONT}>',
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        f'<text x="24" y="34" font-size="20" font-weight="bold" fill="{INK}">{title}</text>',
        f'<text x="24" y="56" font-size="13" fill="{MUTED}">{subtitle}</text>',
        *body, "</svg>"])


def box(cx, cy, w, h, lines, fill="#ffffff", stroke=LINE, boldFirst=True, rx=10, width=2, double=False):
    out = [f'<rect x="{cx - w / 2}" y="{cy - h / 2}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
           f'stroke="{stroke}" stroke-width="{width}"/>']
    if double:
        out.append(f'<rect x="{cx - w / 2 + 4}" y="{cy - h / 2 + 4}" width="{w - 8}" height="{h - 8}" rx="{rx - 3}" '
                   f'fill="none" stroke="{stroke}" stroke-width="1.2"/>')
    y0 = cy - (len(lines) - 1) * 9 + 5
    for i, t in enumerate(lines):
        bold = ' font-weight="bold"' if i == 0 and boldFirst else ""
        size = 14 if i == 0 and boldFirst else 12
        colour = INK if i == 0 else MUTED
        out.append(f'<text x="{cx}" y="{y0 + i * 18}" font-size="{size}"{bold} text-anchor="middle" '
                   f'fill="{colour}">{t}</text>')
    return out


def diamond(cx, cy, w, h, text):
    pts = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
    return [f'<polygon points="{pts}" fill="#fffbeb" stroke="#d97706" stroke-width="2"/>',
            f'<text x="{cx}" y="{cy + 5}" font-size="13" text-anchor="middle" fill="{INK}">{text}</text>']


def label(x, y, text, size=11, colour=MUTED, bg=True, anchor="middle"):
    w = len(text) * size * 0.56 + 8
    left = x - w / 2 if anchor == "middle" else x - 4
    out = [f'<rect x="{left:.1f}" y="{y - size:.1f}" width="{w:.1f}" height="{size + 6}" rx="3" fill="#ffffff"/>'] \
        if bg else []
    out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" fill="{colour}">{text}</text>')
    return out


def arrow(x1, y1, x2, y2, colour=LINE, dashed=False):
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    return [f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{colour}" stroke-width="1.8"'
            f'{dash} marker-end="url(#arrow)"/>']


def clip(cx, cy, w, h, tx, ty):
    """Point where the ray from a box centre towards (tx, ty) leaves the box."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    s = min((w / 2) / abs(dx) if dx else math.inf, (h / 2) / abs(dy) if dy else math.inf)
    return cx + dx * s, cy + dy * s


def curve(a, b, text, bend=0.0, lx=0, ly=0):
    """Arrow between two state boxes (cx, cy, w, h), bent sideways by `bend` × distance."""
    (ax, ay, aw, ah), (bx, by, bw, bh) = a, b
    mx, my = (ax + bx) / 2, (ay + by) / 2
    dx, dy = bx - ax, by - ay
    qx, qy = mx - dy * bend, my + dx * bend
    sx, sy = clip(ax, ay, aw + 6, ah + 6, qx, qy)
    ex, ey = clip(bx, by, bw + 10, bh + 10, qx, qy)
    tx, ty = 0.25 * sx + 0.5 * qx + 0.25 * ex, 0.25 * sy + 0.5 * qy + 0.25 * ey
    out = [f'<path d="M{sx:.1f},{sy:.1f} Q{qx:.1f},{qy:.1f} {ex:.1f},{ey:.1f}" fill="none" stroke="{LINE}" '
           f'stroke-width="1.8" marker-end="url(#arrow)"/>']
    return out, (tx + lx, ty + ly, text)


def selfLoop(node, text, side="top"):
    cx, cy, w, h = node
    if side == "top":
        y = cy - h / 2
        d = f"M{cx - 22},{y} C{cx - 40},{y - 60} {cx + 40},{y - 60} {cx + 22},{y - 2}"
        return [f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.8" marker-end="url(#arrow)"/>'], \
            (cx, y - 52, text)
    y = cy + h / 2
    d = f"M{cx - 22},{y} C{cx - 40},{y + 60} {cx + 40},{y + 60} {cx + 22},{y + 2}"
    return [f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="1.8" marker-end="url(#arrow)"/>'], \
        (cx, y + 60, text)


def reflexFlow():
    body, x, step, w = [], 330, 92, 270
    rules = [("Can I complete a line?", "play the winning cell", "rule 1: WIN"),
             ("Can the opponent complete a line?", "block that cell", "rule 2: BLOCK"),
             ("Is the centre free?", "take the centre", "rule 3: CENTRE"),
             ("Opponent corner with free opposite?", "take the opposite corner", "rule 4: OPPOSITE CORNER"),
             ("Is a corner free?", "take a corner", "rule 5: CORNER")]
    y = 110
    body += box(x, y, 240, 50, ["Percept: current board", "(sensors read all cells)"], "#eff6ff", "#2563eb")
    body += arrow(x, y + 25, x, y + 56)
    y += 92
    for q, act, name in rules:
        body += diamond(x, y, 330, 70, f"{q}")
        body += box(x + 400, y, 250, 52, [name, act], "#f0fdf4", "#16a34a")
        body += arrow(x + 165, y, x + 271, y)
        body += label(x + 218, y - 8, "yes", 12, "#16a34a")
        body += arrow(x, y + 35, x, y + step - 35)
        body += label(x + 18, y + 54, "no", 12, "#dc2626", anchor="start")
        body.append(f'<line x1="{x + 525}" y1="{y}" x2="{x + 600}" y2="{y}" stroke="{LINE}" stroke-width="1.8"/>')
        y += step
    body += box(x, y - 6, 250, 52, ["rule 6: ANY", "take any free cell"], "#f0fdf4", "#16a34a")
    body.append(f'<line x1="{x + 125}" y1="{y - 6}" x2="{x + 600}" y2="{y - 6}" stroke="{LINE}" stroke-width="1.8"/>')
    body.append(f'<line x1="{x + 600}" y1="{202 - 0}" x2="{x + 600}" y2="{y - 6}" stroke="{LINE}" stroke-width="1.8"/>')
    top, bottom = 202, y - 6
    body += box(x + 690, (top + bottom) / 2, 150, 60, ["Actuator", "mark (row, col)"], "#f3f4f6", INK)
    body += arrow(x + 600, (top + bottom) / 2, x + 612, (top + bottom) / 2)
    body += label(x - 150, y + 60, "The agent has no memory: the same board always gives the same move.", 12,
                  MUTED, False, "start")
    return svg(1120, y + 90, body, "Simple reflex agent: condition-action rules",
               "Rules are checked top to bottom; the first one that matches fires (if / elif / else).")


def fsm():
    W, H = 150, 62
    n = {"START": (150, 365), "OPENING": (330, 365), "BUILD": (580, 200), "DEFEND": (580, 530),
         "ATTACK": (890, 530), "FINISH": (890, 200)}
    node = {k: (x, y, W, H) for k, (x, y) in n.items()}
    node["GAME_OVER"] = (1180, 365, 160, H)
    acts = {"START": "no move yet", "OPENING": "take centre or corner", "BUILD": "extend target line",
            "DEFEND": "block / counter-fork", "ATTACK": "play a fork", "FINISH": "play winning cell",
            "GAME_OVER": "absorbing state"}

    body = [f'<rect x="30" y="80" width="1010" height="580" rx="18" fill="#fcfcfd" stroke="#9ca3af" '
            f'stroke-width="1.5" stroke-dasharray="8 5"/>',
            f'<text x="50" y="104" font-size="13" font-weight="bold" fill="{MUTED}">ACTIVE (agent is still playing)'
            f'</text>']
    edges, labels = [], []

    def add(res):
        e, l = res
        edges.extend(e)
        labels.append(l)

    add(curve(node["START"], node["OPENING"], "QUIET", 0, 0, -10))
    add(curve(node["OPENING"], node["BUILD"], "QUIET", 0.1, -30, -4))
    add(curve(node["OPENING"], node["DEFEND"], "MUST_BLOCK / OPP_CAN_FORK", -0.1, -70, 4))
    add(curve(node["BUILD"], node["DEFEND"], "MUST_BLOCK / OPP_CAN_FORK", 0.18, -40, 0))
    add(curve(node["DEFEND"], node["BUILD"], "QUIET", 0.18, 0, 0))
    add(curve(node["BUILD"], node["FINISH"], "CAN_WIN", 0, 0, -8))
    add(curve(node["ATTACK"], node["FINISH"], "CAN_WIN", 0, 34, 0))
    add(curve(node["DEFEND"], node["ATTACK"], "CAN_FORK", -0.12, 0, 0))
    add(curve(node["ATTACK"], node["DEFEND"], "MUST_BLOCK", -0.12, 0, 0))
    # the two diagonals cross in the middle, so their labels sit near the start of each arrow
    e, _ = curve(node["BUILD"], node["ATTACK"], "", 0)
    edges += e
    labels.append((690, 300, "CAN_FORK"))
    e, _ = curve(node["DEFEND"], node["FINISH"], "", 0)
    edges += e
    labels.append((690, 432, "CAN_WIN"))
    add(selfLoop(node["BUILD"], "QUIET: keep or re-plan target line", "top"))
    add(selfLoop(node["DEFEND"], "MUST_BLOCK / OPP_CAN_FORK", "bottom"))

    edges += arrow(1040, 365, 1096, 365)       # GAME_ENDED leaves the whole ACTIVE super-state
    edges.append(f'<circle cx="52" cy="365" r="8" fill="{INK}"/>')
    edges += [f'<line x1="60" y1="365" x2="{150 - W / 2 - 4}" y2="365" stroke="{INK}" stroke-width="1.8" '
              f'marker-end="url(#arrow)"/>']
    body += edges
    for k, (x, y, w, h) in node.items():
        fill, stroke = COLOURS[k]
        body += box(x, y, w, h, [k, acts[k]], fill, stroke, double=(k == "GAME_OVER"),
                    width=2.5 if k in ("START", "GAME_OVER") else 2)
    for x, y, t in labels:
        if t:
            body += label(x, y, t)
    body += label(1068, 335, "GAME_ENDED", 11, INK)
    body += label(1068, 351, "(any state)", 10)

    notes = ["Events are computed from the percept + internal model and checked in priority order:",
             "GAME_ENDED > CAN_WIN > MUST_BLOCK > CAN_FORK > OPP_CAN_FORK > QUIET.",
             "From every active state: CAN_WIN → FINISH, MUST_BLOCK or OPP_CAN_FORK → DEFEND, CAN_FORK → ATTACK,",
             "QUIET → BUILD (QUIET → OPENING only from START). Arrows show the transitions that can occur in play."]
    for i, t in enumerate(notes):
        body += label(50, 692 + i * 18, t, 12, MUTED, False, "start")
    return svg(1290, 770, body, "Model-based agent: finite state machine",
               "next_state = TRANSITIONS[(current_state, event)]; each state has its own action.")


def modelAgent():
    body = []
    # agent boundary
    body.append('<rect x="30" y="80" width="760" height="520" rx="16" fill="#fcfcfd" stroke="#9ca3af" '
                'stroke-width="1.5" stroke-dasharray="8 5"/>')
    body += label(50, 104, "MODEL-BASED AGENT", 13, MUTED, False, "start")
    body.append('<rect x="830" y="80" width="230" height="520" rx="16" fill="#f0f9ff" stroke="#0284c7" '
                'stroke-width="1.5"/>')
    body += label(945, 104, "ENVIRONMENT", 13, "#0369a1", False)
    body += box(945, 250, 190, 120, ["m×m board", "opponent agent", "turn order X, O", "k-in-a-row rule"],
                "#ffffff", "#0284c7")
    body += box(945, 470, 190, 60, ["Opponent move", "changes the board"], "#ffffff", "#0284c7")

    body += box(680, 160, 170, 56, ["Sensors", "read every cell"], "#eff6ff", "#2563eb")
    body += box(680, 520, 170, 56, ["Actuators", "place mark (r, c)"], "#f3f4f6", INK)
    body += box(420, 160, 270, 64, ["What the board is like now", "updateModel(): diff with previous board"],
                "#ffffff", LINE)
    body += box(150, 250, 200, 112, ["Internal state", "previous board", "my / opponent moves", "target line",
                                     "FSM state"], "#f5f3ff", "#7c3aed")
    body += box(150, 420, 200, 76, ["Transition model", "result(board, move):", "predict forks 1 move ahead"],
                "#f5f3ff", "#7c3aed")
    body += box(420, 300, 270, 64, ["Event detector", "CAN_WIN, MUST_BLOCK, CAN_FORK, …"], "#fffbeb", "#d97706")
    body += box(420, 420, 270, 64, ["Finite state machine", "TRANSITIONS[(state, event)]"], "#fef2f2", "#dc2626")
    body += box(420, 530, 270, 56, ["State action", "OPENING / BUILD / DEFEND / …"], "#f0fdf4", "#16a34a")

    body += arrow(850, 200, 767, 168)          # env -> sensors
    body += arrow(595, 160, 557, 160)          # sensors -> world now
    body += arrow(285, 168, 252, 210)          # world now -> internal state
    body += arrow(250, 270, 285, 290)          # internal state -> event detector
    body += arrow(250, 420, 285, 420)          # transition model -> fsm/event
    body += arrow(250, 400, 285, 320)
    body += arrow(420, 332, 420, 386)          # event -> fsm
    body += arrow(420, 452, 420, 500)          # fsm -> action
    body += arrow(555, 530, 593, 528)          # action -> actuators
    body += arrow(767, 520, 848, 480)          # actuators -> env
    body.append(f'<path d="M305,420 C220,520 120,520 120,306" fill="none" stroke="{LINE}" stroke-width="1.5" '
                'stroke-dasharray="6 4" marker-end="url(#arrow)"/>')
    body += label(205, 528, "FSM state, target line and my move are stored", 11)
    body.append(f'<path d="M945,440 L945,312" fill="none" stroke="#0284c7" stroke-width="1.5" '
                'marker-end="url(#arrow)"/>')
    return svg(1090, 630, body, "Model-based agent architecture",
               "Percept → update internal model → detect event → FSM transition → state action → actuator.")


def main():
    os.makedirs("diagrams", exist_ok=True)
    for name, fn in (("reflex_flow", reflexFlow), ("fsm", fsm), ("model_agent", modelAgent)):
        path = os.path.join("diagrams", name + ".svg")
        with open(path, "w") as f:
            f.write(fn())
        print("wrote", path)


if __name__ == "__main__":
    main()
