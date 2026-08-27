"""Solveur de placement PCB.

Chaque composant a une position souhaitee (l'intention de plan de masse) et
eventuellement un verrou. Une relaxation iterative ecarte les contours de
courtoisie qui se chevauchent tout en gardant chacun pres de son ancre et
a l'interieur de la carte.

Lance directement, ce script reecrit le dictionnaire PCB_PLACE de design.py.
"""
import re

import fputil
import design as D

CLEARANCE = 0.25        # marge supplementaire entre contours de courtoisie
EDGE_MARGIN = 0.30      # retrait minimal par rapport au bord de carte
ITER = 4000
SNAP = 0.05

# --------------------------------------------------------------------------
# Plan de masse : carte 48 x 52 mm, x 100..148, y 100..152
#   y = 100  -> AVANT du boitier (capteur ToF, ecran juste au-dessus)
#   y = 152  -> ARRIERE (sortie USB-C)
#   x = 100  -> flanc GAUCHE (trappe microSD)
# ref: (x, y, rotation, verrouille, peut_deborder)
# --------------------------------------------------------------------------
ANCHORS = {
    # --- bord avant ---
    "U4":  (128.0, 102.6,   0, True,  False),   # ToF, vise vers le haut
    "C15": (134.0, 103.0,   0, False, False),
    "C16": (131.0, 106.0,   0, False, False),
    "C17": (125.0, 106.0,   0, False, False),
    "R15": (122.0, 103.0,   0, False, False),
    "R16": (122.0, 105.0,   0, False, False),
    "U5":  (112.0, 103.5,   0, False, False),   # accelerometre
    "C18": (107.5, 102.5,   0, False, False),
    "C19": (107.5, 105.0,   0, False, False),
    "R19": (116.0, 103.0,   0, False, False),
    "R17": (116.0, 106.5,   0, False, False),
    "R18": (119.0, 106.5,   0, False, False),

    # --- connecteur ecran, juste sous le bord avant ---
    "J2":  (124.0, 110.5,   0, True,  False),
    "R6":  (136.5, 110.0,   0, False, False),
    "TP4": (140.0, 110.5,   0, False, False),

    # --- module MCU, centre ---
    "U2":  (124.0, 126.5,   0, True,  False),
    "C8":  (113.5, 137.5,   0, False, False),
    "C9":  (116.5, 137.5,   0, False, False),

    # --- flanc gauche : microSD (fente vers l'exterieur) ---
    "J3":  (107.2, 124.0, 270, True,  False),
    "R7":  (101.5, 133.5,   0, False, False),
    "R8":  (101.5, 135.0,   0, False, False),
    "R9":  (104.5, 133.5,   0, False, False),
    "R10": (104.5, 135.0,   0, False, False),
    "R11": (107.5, 133.5,   0, False, False),
    "R12": (107.5, 135.0,   0, False, False),
    "C11": (102.0, 131.0,  90, False, False),
    "C12": (104.5, 131.0,   0, False, False),
    "J5":  (104.0, 113.0, 270, False, False),   # port I2C deporte

    # --- flanc droit : audio ---
    "FB1": (140.0, 116.5,   0, False, False),
    "U3":  (140.5, 121.0,   0, False, False),
    "C13": (145.0, 118.0,  90, False, False),
    "C14": (145.0, 122.0,  90, False, False),
    "R13": (140.0, 126.0,   0, False, False),
    "R14": (140.0, 128.0,   0, False, False),
    "J4":  (143.5, 132.0,  90, False, False),

    # --- arriere gauche : regulateur ---
    "L1":  (104.0, 143.0,   0, False, False),
    "U1":  (109.5, 143.0,   0, False, False),
    "C3":  (109.5, 139.5,   0, False, False),
    "R3":  (113.0, 139.5,   0, False, False),
    "C1":  (114.0, 143.5,  90, False, False),
    "C2":  (114.0, 147.0,   0, False, False),
    "C4":  (101.5, 139.5,  90, False, False),
    "C5":  (104.0, 139.0,   0, False, False),
    "C6":  (101.5, 147.0,   0, False, False),
    "C7":  (117.0, 143.5,  90, False, False),
    "F1":  (117.0, 147.5,   0, False, False),

    # --- arriere centre : USB-C (deborde volontairement du bord) ---
    "J1":  (124.0, 149.5,   0, True,  True),
    "R1":  (129.0, 139.0,   0, False, False),
    "R2":  (131.5, 139.0,   0, False, False),
    "D1":  (133.5, 142.5,   0, False, False),

    # --- arriere droit : boutons + debug ---
    "SW1": (134.5, 147.5,   0, False, False),
    "SW2": (139.5, 147.5,   0, False, False),
    "R4":  (134.5, 144.5,   0, False, False),
    "C10": (137.5, 144.5,   0, False, False),
    "R5":  (140.5, 142.0,   0, False, False),
    "J6":  (135.5, 138.5,   0, False, False),
    "TP1": (120.0, 139.0,   0, False, False),
    "TP2": (123.0, 139.0,   0, False, False),
    "TP3": (126.0, 139.0,   0, False, False),

    # --- trous de fixation M2, verrouilles dans les coins ---
    "H1":  (103.0, 103.0,   0, True,  False),
    "H2":  (145.0, 103.0,   0, True,  False),
    "H3":  (103.0, 149.0,   0, True,  False),
    "H4":  (145.0, 149.0,   0, True,  False),
}


def solve(verbose=True):
    X0, Y0 = D.BOARD_X, D.BOARD_Y
    X1, Y1 = D.BOARD_X + D.BOARD_W, D.BOARD_Y + D.BOARD_H

    refs = list(ANCHORS)
    pos = {r: [ANCHORS[r][0], ANCHORS[r][1]] for r in refs}
    rot = {r: ANCHORS[r][2] for r in refs}
    lock = {r: ANCHORS[r][3] for r in refs}
    overhang = {r: ANCHORS[r][4] for r in refs}
    box = {r: fputil.courtyard_box(D.PARTS[r]["fp"], rot[r]) for r in refs}

    for it in range(ITER):
        moved = 0.0
        # 1. separation par paires
        for i in range(len(refs)):
            for j in range(i + 1, len(refs)):
                a, b = refs[i], refs[j]
                ax, ay = pos[a]; bx, by = pos[b]
                a0, a1, a2, a3 = box[a]
                b0, b1, b2, b3 = box[b]
                ox = min(ax + a2, bx + b2) - max(ax + a0, bx + b0) + CLEARANCE
                oy = min(ay + a3, by + b3) - max(ay + a1, by + b1) + CLEARANCE
                if ox <= 0 or oy <= 0:
                    continue
                # ecarter selon l'axe de moindre penetration
                if ox < oy:
                    d = ox / 2.0
                    s = 1.0 if (ax + (a0 + a2) / 2) < (bx + (b0 + b2) / 2) else -1.0
                    if not lock[a]: pos[a][0] -= s * d
                    if not lock[b]: pos[b][0] += s * d
                else:
                    d = oy / 2.0
                    s = 1.0 if (ay + (a1 + a3) / 2) < (by + (b1 + b3) / 2) else -1.0
                    if not lock[a]: pos[a][1] -= s * d
                    if not lock[b]: pos[b][1] += s * d
                moved += d

        # 2. rappel vers l'ancre + confinement dans la carte
        for r in refs:
            if lock[r]:
                continue
            ax, ay, *_ = ANCHORS[r]
            k = 0.03 * (1.0 - it / float(ITER)) ** 2
            pos[r][0] += (ax - pos[r][0]) * k
            pos[r][1] += (ay - pos[r][1]) * k
            b0, b1, b2, b3 = box[r]
            if not overhang[r]:
                pos[r][0] = min(max(pos[r][0], X0 + EDGE_MARGIN - b0), X1 - EDGE_MARGIN - b2)
                pos[r][1] = min(max(pos[r][1], Y0 + EDGE_MARGIN - b1), Y1 - EDGE_MARGIN - b3)

        if moved < 1e-4 and it > 50:
            break

    for r in refs:
        pos[r][0] = round(round(pos[r][0] / SNAP) * SNAP, 3)
        pos[r][1] = round(round(pos[r][1] / SNAP) * SNAP, 3)

    # --- rapport ---
    bad = []
    for i in range(len(refs)):
        for j in range(i + 1, len(refs)):
            a, b = refs[i], refs[j]
            ax, ay = pos[a]; bx, by = pos[b]
            a0, a1, a2, a3 = box[a]; b0, b1, b2, b3 = box[b]
            ox = min(ax + a2, bx + b2) - max(ax + a0, bx + b0)
            oy = min(ay + a3, by + b3) - max(ay + a1, by + b1)
            if ox > 0.01 and oy > 0.01:
                bad.append((a, b, round(ox, 2), round(oy, 2)))
    outside = []
    for r in refs:
        if overhang[r]:
            continue
        b0, b1, b2, b3 = box[r]
        x, y = pos[r]
        if x + b0 < X0 - 0.01 or y + b1 < Y0 - 0.01 or x + b2 > X1 + 0.01 or y + b3 > Y1 + 0.01:
            outside.append((r, round(x + b0, 2), round(y + b1, 2), round(x + b2, 2), round(y + b3, 2)))
    if verbose:
        print("iterations : %d" % (it + 1))
        print("chevauchements restants : %d %s" % (len(bad), bad[:10] if bad else ""))
        print("composants hors carte   : %d %s" % (len(outside), outside[:10] if outside else ""))
        dev = sorted(((abs(pos[r][0] - ANCHORS[r][0]) + abs(pos[r][1] - ANCHORS[r][1]), r)
                      for r in refs), reverse=True)[:6]
        print("plus grands ecarts a l'ancre : %s" % [(r, round(d, 2)) for d, r in dev])
    return pos, rot, bad, outside


def write_back(pos, rot):
    body = ["PCB_PLACE = {"]
    order = list(D.PARTS)
    for r in order:
        body.append('    "%s": (%.2f, %.2f, %d, "F.Cu"),' % (r, pos[r][0], pos[r][1], rot[r]))
    body.append("}")
    new = "\n".join(body)
    path = "design.py"
    src = open(path, encoding="utf-8").read()
    src = re.sub(r"PCB_PLACE = \{.*?\n\}", new, src, flags=re.S)
    open(path, "w", encoding="utf-8").write(src)
    print("PCB_PLACE reecrit dans design.py (%d composants)" % len(order))


if __name__ == "__main__":
    p, r, bad, out = solve()
    if not bad and not out:
        write_back(p, r)
    else:
        print("!! placement non convergent - design.py inchange")
