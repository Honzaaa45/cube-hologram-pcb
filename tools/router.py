"""Routeur pour hw/cube.kicad_pcb.

Deux mecanismes complementaires :

  * GND et +3V3 sont des plans (In1.Cu / In2.Cu). Chaque pastille CMS de ces
    nets recoit simplement un via de couture place au plus pres.
  * Les autres nets sont routes en labyrinthe (Dijkstra 8 directions) sur
    F.Cu et B.Cu, avec changement de couche par via.

La grille d'obstacles est tenue en deux versions - une gonflee pour les pistes
fines, une pour les pistes de puissance - afin que chaque net voie la bonne
isolation.
"""
import heapq
import math
import os
from array import array

import fputil
import design as D

HW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hw")
PCB = os.path.join(HW, "cube.kicad_pcb")

GRID = 0.1                 # pas de la grille de routage (mm)
MARGIN = 1.0               # marge autour de la carte
CLEAR = 0.13               # isolation cuivre-cuivre (limite JLCPCB 4 couches)
EDGE_KEEPOUT = 0.35        # retrait du bord de carte

W_SIG, W_PWR = 0.15, 0.5   # largeurs de piste
VIA_D, VIA_DRILL = 0.5, 0.3
HOLE_CLEAR = 0.25          # percage <-> percage / percage <-> cuivre

# Demi-encombrement de ce que le routeur POSE, par classe. Toute inflation
# d'obstacle doit l'inclure, sinon deux pistes voisines se touchent.
PLACE_HALF = (W_SIG / 2, max(W_PWR / 2, VIA_D / 2))

PLANE_NETS = {"GND": "In1.Cu", "+3V3": "In2.Cu"}
POWER_NETS = {"+5V", "VBUS", "VDD_AMP", "SW_NODE", "BST"}

BLOCKED = -1
FREE = 0


def in_pad(shape, lx, ly, w, h, extra=0.0):
    """Le point local (lx, ly) est-il dans la pastille gonflee de `extra` ?"""
    if shape == "circle":
        r = min(w, h) / 2 + extra
        return lx * lx + ly * ly <= r * r
    if shape == "oval":
        if w >= h:
            r = h / 2 + extra
            flat = (w - h) / 2
            if abs(lx) <= flat:
                return abs(ly) <= r
            dx = abs(lx) - flat
            return dx * dx + ly * ly <= r * r
        r = w / 2 + extra
        flat = (h - w) / 2
        if abs(ly) <= flat:
            return abs(lx) <= r
        dy = abs(ly) - flat
        return lx * lx + dy * dy <= r * r
    return abs(lx) <= w / 2 + extra and abs(ly) <= h / 2 + extra

# ordre de routage : le plus critique et le plus court d'abord
PRIORITY = ["SW_NODE", "BST", "VBUS", "+5V", "VDD_AMP", "VREG_EN",
            "USB_DP", "USB_DM", "CC1", "CC2",
            "LCD_SCK_MCU", "LCD_SCK", "LCD_D0", "LCD_D1", "LCD_D2", "LCD_D3",
            "LCD_CS", "LCD_RST", "LCD_TE", "LCD_PWR_EN",
            "SD_CLK", "SD_CMD", "SD_D0", "SD_D1", "SD_D2", "SD_D3", "SD_DET",
            "I2S_BCLK", "I2S_LRCLK", "I2S_DOUT", "AMP_EN", "AMP_GAIN",
            "SPK_P", "SPK_N",
            "I2C_SDA", "I2C_SCL", "TOF_XSHUT", "TOF_INT", "ACC_INT1", "ACC_ADDR",
            "EN", "BOOT", "UART_TX", "UART_RX"]


# --------------------------------------------------------------------------
# Grille
# --------------------------------------------------------------------------
class Grid:
    def __init__(self, x0, y0, x1, y1):
        self.ox, self.oy = x0 - MARGIN, y0 - MARGIN
        self.w = int((x1 - x0 + 2 * MARGIN) / GRID) + 1
        self.h = int((y1 - y0 + 2 * MARGIN) / GRID) + 1
        # [couche][classe]  couche 0 = F.Cu, 1 = B.Cu ; classe 0 = signal, 1 = puissance
        self.g = [[array("i", [FREE]) * (self.w * self.h) for _ in range(2)]
                  for _ in range(2)]
        # 1 = aucun via ne peut etre perce ici (trop pres d'un autre trou)
        self.drill = array("b", [0]) * (self.w * self.h)

    def stamp_drill(self, cx, cy, hole_r):
        rr = hole_r + HOLE_CLEAR + VIA_DRILL / 2
        i0, j0 = self.cell(cx - rr, cy - rr)
        i1, j1 = self.cell(cx + rr, cy + rr)
        for j in range(max(0, j0), min(self.h, j1 + 1)):
            for i in range(max(0, i0), min(self.w, i1 + 1)):
                px, py = self.pos(i, j)
                if (px - cx) ** 2 + (py - cy) ** 2 <= rr * rr:
                    self.drill[j * self.w + i] = 1

    def snapshot(self):
        return ([[a[:] for a in L] for L in self.g], self.drill[:])

    def restore(self, snap):
        self.g = [[a[:] for a in L] for L in snap[0]]
        self.drill = snap[1][:]

    def cell(self, x, y):
        return (int(round((x - self.ox) / GRID)), int(round((y - self.oy) / GRID)))

    def pos(self, cx, cy):
        return (self.ox + cx * GRID, self.oy + cy * GRID)

    def inside(self, cx, cy):
        return 0 <= cx < self.w and 0 <= cy < self.h

    def stamp_pad(self, layers, cx, cy, w, h, ang, net, extra, shape="rect"):
        """Marque une pastille (forme exacte) gonflee de `extra`, par classe."""
        for cls, ex in enumerate(extra):
            hw, hh = w / 2 + ex, h / 2 + ex
            rad = math.hypot(hw, hh)
            i0, j0 = self.cell(cx - rad, cy - rad)
            i1, j1 = self.cell(cx + rad, cy + rad)
            ca, sa = math.cos(math.radians(-ang)), math.sin(math.radians(-ang))
            for j in range(max(0, j0), min(self.h, j1 + 1)):
                for i in range(max(0, i0), min(self.w, i1 + 1)):
                    px, py = self.pos(i, j)
                    dx, dy = px - cx, py - cy
                    lx = dx * ca + dy * sa
                    ly = -dx * sa + dy * ca
                    if in_pad(shape, lx, ly, w, h, ex):
                        for L in layers:
                            k = j * self.w + i
                            cur = self.g[L][cls][k]
                            if cur == FREE:
                                self.g[L][cls][k] = net
                            elif cur != net:
                                self.g[L][cls][k] = BLOCKED

    def stamp_disc(self, layers, cx, cy, r, net, extra):
        for cls, ex in enumerate(extra):
            rr = r + ex
            i0, j0 = self.cell(cx - rr, cy - rr)
            i1, j1 = self.cell(cx + rr, cy + rr)
            for j in range(max(0, j0), min(self.h, j1 + 1)):
                for i in range(max(0, i0), min(self.w, i1 + 1)):
                    px, py = self.pos(i, j)
                    if (px - cx) ** 2 + (py - cy) ** 2 <= rr * rr:
                        for L in layers:
                            k = j * self.w + i
                            cur = self.g[L][cls][k]
                            if cur == FREE:
                                self.g[L][cls][k] = net
                            elif cur != net:
                                self.g[L][cls][k] = BLOCKED

    def force_pad(self, layers, cx, cy, w, h, ang, net, shape="rect"):
        """Ecrit sans conflit : le cuivre de la pastille appartient a son net.

        On retreint legerement (0.05 mm) pour qu'une extremite de piste tombe
        franchement dans le cuivre et non sur son bord.
        """
        hw, hh = w / 2, h / 2
        rad = math.hypot(hw, hh)
        i0, j0 = self.cell(cx - rad, cy - rad)
        i1, j1 = self.cell(cx + rad, cy + rad)
        ca, sa = math.cos(math.radians(-ang)), math.sin(math.radians(-ang))
        out = []
        for j in range(max(0, j0), min(self.h, j1 + 1)):
            for i in range(max(0, i0), min(self.w, i1 + 1)):
                px, py = self.pos(i, j)
                dx, dy = px - cx, py - cy
                lx = dx * ca + dy * sa
                ly = -dx * sa + dy * ca
                if in_pad(shape, lx, ly, w, h, -0.05):
                    out.append((i, j))
                    for L in layers:
                        for cls in (0, 1):
                            self.g[L][cls][j * self.w + i] = net
        if not out:   # pastille minuscule : garder au moins la cellule centrale
            i, j = self.cell(cx, cy)
            out.append((i, j))
            for L in layers:
                for cls in (0, 1):
                    self.g[L][cls][j * self.w + i] = net
        return out


# --------------------------------------------------------------------------
# Construction du modele
# --------------------------------------------------------------------------
def build_model():
    x0, y0 = D.BOARD_X, D.BOARD_Y
    x1, y1 = D.BOARD_X + D.BOARD_W, D.BOARD_Y + D.BOARD_H
    g = Grid(x0, y0, x1, y1)

    # bord de carte : tout ce qui est hors du contour retreci est interdit
    for j in range(g.h):
        for i in range(g.w):
            px, py = g.pos(i, j)
            if not (x0 + EDGE_KEEPOUT <= px <= x1 - EDGE_KEEPOUT and
                    y0 + EDGE_KEEPOUT <= py <= y1 - EDGE_KEEPOUT):
                k = j * g.w + i
                for L in (0, 1):
                    for cls in (0, 1):
                        g.g[L][cls][k] = BLOCKED

    nets = {"": 0}
    for i, n in enumerate(sorted(D.NETS), start=1):
        nets[n] = i
    padmap = {}
    for n, conns in D.NETS.items():
        for ref, pin in conns:
            padmap[(ref, pin)] = n

    pad_cells = {}     # (ref, pin) -> [cellules]
    pad_info = {}      # (ref, pin) -> (x, y, couches, net)
    extra = (CLEAR + PLACE_HALF[0], CLEAR + PLACE_HALF[1])

    for ref, part in D.PARTS.items():
        px, py, rot, _ = D.PCB_PLACE[ref]
        for num, ax, ay, pw, ph, pang, ptype, players, drill, shape in fputil.abs_pads(part["fp"], px, py, rot):
            netname = padmap.get((ref, num), "")
            nid = nets.get(netname, 0) if netname else BLOCKED
            if ptype in ("thru_hole", "np_thru_hole"):
                layers = [0, 1]
            elif "B.Cu" in players:
                layers = [1]
            elif "F.Cu" in players:
                layers = [0]
            else:
                layers = []          # pastille non cuivree (masque seul)
            if not layers:
                continue
            if drill:
                g.stamp_drill(ax, ay, drill / 2)
            if ptype == "np_thru_hole":
                # trou non metallise : c'est l'isolation des TROUS qui prime
                # sur l'isolation cuivre, plus stricte de 0.12 mm ici.
                g.stamp_disc([0, 1], ax, ay, max(pw, ph) / 2, BLOCKED,
                             (HOLE_CLEAR + PLACE_HALF[0], HOLE_CLEAR + PLACE_HALF[1]))
                continue
            ex = extra
            if drill:
                # pastille traversante : la couronne peut etre plus etroite que
                # l'isolation exigee autour du trou lui-meme
                need = max(CLEAR, HOLE_CLEAR - (min(pw, ph) - drill) / 2)
                ex = (need + PLACE_HALF[0], need + PLACE_HALF[1])
            g.stamp_pad(layers, ax, ay, pw, ph, pang, nid, ex, shape)
            if netname:
                pad_info[(ref, num)] = (ax, ay, layers, netname, min(pw, ph))

    # les pastilles ecrasent les zones gonflees voisines
    for ref, part in D.PARTS.items():
        px, py, rot, _ = D.PCB_PLACE[ref]
        for num, ax, ay, pw, ph, pang, ptype, players, drill, shape in fputil.abs_pads(part["fp"], px, py, rot):
            if (ref, num) not in pad_info:
                continue
            layers = pad_info[(ref, num)][2]
            nid = nets[pad_info[(ref, num)][3]]
            pad_cells[(ref, num)] = g.force_pad(layers, ax, ay, pw, ph, pang, nid, shape)

    return g, nets, pad_info, pad_cells


# --------------------------------------------------------------------------
# Recherche de chemin
# --------------------------------------------------------------------------
STEPS = [(1, 0, 10), (-1, 0, 10), (0, 1, 10), (0, -1, 10),
         (1, 1, 14), (1, -1, 14), (-1, 1, 14), (-1, -1, 14)]
VIA_COST = 100


def route_one(g, nid, sources, targets, cls, allow_via=True, bbox=None):
    """Dijkstra multi-source. Retourne [(i, j, couche)] ou None."""
    W, H = g.w, g.h
    tset = set(targets)      # triplets (i, j, couche)
    dist = {}
    prev = {}
    viamemo = {}
    pq = []
    for (i, j, L) in sources:
        s = (i, j, L)
        dist[s] = 0
        heapq.heappush(pq, (0, s))
    goal = None
    while pq:
        d, cur = heapq.heappop(pq)
        if d > dist.get(cur, 1 << 30):
            continue
        if cur in tset:
            goal = cur
            break
        i, j, L = cur
        for di, dj, c in STEPS:
            ni, nj = i + di, j + dj
            if not (0 <= ni < W and 0 <= nj < H):
                continue
            if bbox and not (bbox[0] <= ni <= bbox[2] and bbox[1] <= nj <= bbox[3]):
                continue
            v = g.g[L][cls][nj * W + ni]
            if v != FREE and v != nid:
                continue
            if di and dj:      # diagonale : les deux cases orthogonales doivent passer
                a = g.g[L][cls][j * W + ni]
                b = g.g[L][cls][nj * W + i]
                if (a != FREE and a != nid) or (b != FREE and b != nid):
                    continue
            nd = d + c
            nk = (ni, nj, L)
            if nd < dist.get(nk, 1 << 30):
                dist[nk] = nd
                prev[nk] = cur
                heapq.heappush(pq, (nd, nk))
        if allow_via:
            L2 = 1 - L
            k = (i, j)
            okv = viamemo.get(k)
            if okv is None:
                okv = via_ok(g, nid, i, j)
                viamemo[k] = okv
            if okv:
                nk = (i, j, L2)
                nd = d + VIA_COST
                if nd < dist.get(nk, 1 << 30):
                    dist[nk] = nd
                    prev[nk] = cur
                    heapq.heappush(pq, (nd, nk))
    if goal is None:
        return None
    path = [goal]
    while path[-1] in prev:
        path.append(prev[path[-1]])
    path.reverse()
    return path


def stamp_path(g, nid, cells, cls_widths):
    """Marque le couloir d'une piste deja tracee."""
    for cls, hw in enumerate(cls_widths):
        r = hw + CLEAR + PLACE_HALF[cls]
        for (i, j, L) in cells:
            px, py = g.pos(i, j)
            i0, j0 = g.cell(px - r, py - r)
            i1, j1 = g.cell(px + r, py + r)
            for jj in range(max(0, j0), min(g.h, j1 + 1)):
                for ii in range(max(0, i0), min(g.w, i1 + 1)):
                    qx, qy = g.pos(ii, jj)
                    if (qx - px) ** 2 + (qy - py) ** 2 <= r * r:
                        k = jj * g.w + ii
                        cur = g.g[L][cls][k]
                        if cur == FREE:
                            g.g[L][cls][k] = nid
                        elif cur != nid:
                            g.g[L][cls][k] = BLOCKED


def stamp_via(g, nid, i, j, vd=None, vdrill=None):
    """Reserve la place d'un via. `vd`/`vdrill` permettent de re-empreindre un
    via existant a sa vraie taille, meme si la passe courante en pose d'autres.
    """
    vd = VIA_D if vd is None else vd
    vdrill = VIA_DRILL if vdrill is None else vdrill
    px, py = g.pos(i, j)
    g.stamp_drill(px, py, vdrill / 2)
    # Deux contraintes se disputent le rayon a reserver autour d'un via :
    #   - cuivre <-> cuivre : rayon de pastille + CLEAR
    #   - percage <-> cuivre : rayon de percage + HOLE_CLEAR (souvent pire)
    base = max(vd / 2 + CLEAR, vdrill / 2 + HOLE_CLEAR)
    for cls, ex in enumerate(PLACE_HALF):
        rr = base + ex
        i0, j0 = g.cell(px - rr, py - rr)
        i1, j1 = g.cell(px + rr, py + rr)
        for jj in range(max(0, j0), min(g.h, j1 + 1)):
            for ii in range(max(0, i0), min(g.w, i1 + 1)):
                qx, qy = g.pos(ii, jj)
                if (qx - px) ** 2 + (qy - py) ** 2 <= rr * rr:
                    k = jj * g.w + ii
                    for L in (0, 1):
                        cur = g.g[L][cls][k]
                        if cur == FREE:
                            g.g[L][cls][k] = nid
                        elif cur != nid:
                            g.g[L][cls][k] = BLOCKED


def via_ok(g, nid, i, j, cls=1):
    """Un via peut-il etre pose ici ?

    On teste toujours en classe 1 : un via a le meme demi-encombrement qu'une
    piste de puissance. On verifie aussi le masque de percage, car deux trous
    doivent respecter une distance meme s'ils sont du meme net.
    """
    if g.drill[j * g.w + i]:
        return False
    cls = 1
    r = VIA_D / 2 + CLEAR
    px, py = g.pos(i, j)
    i0, j0 = g.cell(px - r, py - r)
    i1, j1 = g.cell(px + r, py + r)
    for jj in range(j0, j1 + 1):
        for ii in range(i0, i1 + 1):
            if not g.inside(ii, jj):
                return False
            qx, qy = g.pos(ii, jj)
            if (qx - px) ** 2 + (qy - py) ** 2 > r * r:
                continue
            k = jj * g.w + ii
            for L in (0, 1):
                v = g.g[L][cls][k]
                if v != FREE and v != nid:
                    return False
    return True


def simplify(g, path):
    """Chemin en cellules -> segments droits + vias."""
    segs, vias = [], []
    run = [path[0]]
    for k in range(1, len(path)):
        a, b = path[k - 1], path[k]
        if a[2] != b[2]:                      # changement de couche = via
            if len(run) > 1:
                segs.extend(_runsegs(g, run))
            vias.append(g.pos(a[0], a[1]))
            run = [b]
        else:
            run.append(b)
    if len(run) > 1:
        segs.extend(_runsegs(g, run))
    return segs, vias


def _runsegs(g, run):
    """Une suite de cellules coplanaires -> segments droits."""
    out = []
    start = 0
    def direction(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        return ((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))
    cur_dir = direction(run[0], run[1])
    for k in range(1, len(run)):
        d = direction(run[k - 1], run[k])
        if d != cur_dir:
            out.append((g.pos(*run[start][:2]), g.pos(*run[k - 1][:2]), run[0][2]))
            start = k - 1
            cur_dir = d
    out.append((g.pos(*run[start][:2]), g.pos(*run[-1][:2]), run[0][2]))
    return [s for s in out if s[0] != s[1]]


# --------------------------------------------------------------------------
# Couture des plans : un via par pastille CMS de GND / +3V3
# --------------------------------------------------------------------------
def line_clear(g, nid, a, b, cls, layer):
    """La droite a->b est-elle franchissable sur `layer` ?"""
    n = max(abs(b[0] - a[0]), abs(b[1] - a[1]))
    for t in range(n + 1):
        i = a[0] + (b[0] - a[0]) * t // max(1, n)
        j = a[1] + (b[1] - a[1]) * t // max(1, n)
        if not g.inside(i, j):
            return False
        v = g.g[layer][cls][j * g.w + i]
        if v != FREE and v != nid:
            return False
    return True


def stitch_planes(g, nets, pad_info, plane_cells=None):
    """Un via par pastille CMS de plan. En dernier recours, on rejoint le
    cuivre deja pose du meme net plutot que d'echouer."""
    tracks, vias = [], []
    plane_cells = plane_cells if plane_cells is not None else {}
    done = fail = 0
    for (ref, pin), (ax, ay, layers, netname, psize) in sorted(pad_info.items()):
        if netname not in PLANE_NETS:
            continue
        if 0 in layers and 1 in layers:
            done += 1          # pastille traversante : deja reliee aux plans
            continue
        nid = nets[netname]
        layer = layers[0]
        cls = 1 if netname in POWER_NETS or netname in PLANE_NETS else 0
        pc = g.cell(ax, ay)
        best = None
        for rad in [x * 0.1 for x in range(4, 22)]:
            steps = max(8, int(2 * math.pi * rad / GRID / 2))
            for k in range(steps):
                th = 2 * math.pi * k / steps
                ci, cj = g.cell(ax + rad * math.cos(th), ay + rad * math.sin(th))
                if not g.inside(ci, cj):
                    continue
                if not via_ok(g, nid, ci, cj):
                    continue
                if not line_clear(g, nid, pc, (ci, cj), cls, layer):
                    continue
                best = (ci, cj)
                break
            if best:
                break
        if not best:
            # repli : rejoindre le cuivre du meme net deja en place
            got = plane_cells.get(netname)
            if got:
                srcs = [(i, j, layer) for (i, j) in pad_cells_of(g, ax, ay)]
                path = route_one(g, nid, srcs, got, cls)
                if path:
                    wf = max(W_SIG, min(W_PWR, psize - 0.05))
                    stamp_path(g, nid, path, (wf / 2, wf / 2))
                    segs, vs = simplify(g, path)
                    for a, b, L in segs:
                        tracks.append((a, b, L, netname, wf))
                    for v in vs:
                        stamp_via(g, nid, *g.cell(*v))
                        vias.append((v, netname))
                    plane_cells.setdefault(netname, set()).update(path)
                    done += 1
                    continue
            fail += 1
            continue
        cells = []
        n = max(abs(best[0] - pc[0]), abs(best[1] - pc[1]))
        for t in range(n + 1):
            cells.append((pc[0] + (best[0] - pc[0]) * t // max(1, n),
                          pc[1] + (best[1] - pc[1]) * t // max(1, n), layer))
        wstub = max(W_SIG, min(W_PWR, psize - 0.05))
        stamp_path(g, nid, cells, (wstub / 2, wstub / 2))
        stamp_via(g, nid, best[0], best[1])
        p1, p2 = g.pos(*pc), g.pos(*best)
        if p1 != p2:
            tracks.append((p1, p2, layer, netname, wstub))
        vias.append((p2, netname))
        s = plane_cells.setdefault(netname, set())
        s.update(cells)
        s.update({(best[0], best[1], 0), (best[0], best[1], 1)})
        done += 1
    return tracks, vias, done, fail


def pad_cells_of(g, ax, ay):
    """Cellules autour du centre d'une pastille (point de depart du repli)."""
    i, j = g.cell(ax, ay)
    return [(i, j)]


# --------------------------------------------------------------------------
# Routage des signaux
# --------------------------------------------------------------------------
def route_signals(g, nets, pad_info, pad_cells, order=None, passes=3):
    """Route les nets de signal. Plusieurs passes : la grille evolue, une
    liaison impossible au debut peut passer une fois d'autres pistes posees."""
    tracks, vias = [], []
    if order is None:
        order = [n for n in PRIORITY if n in D.NETS]
        order += [n for n in D.NETS if n not in order and n not in PLANE_NETS]

    # etat par net : cellules deja reliees + pastilles restantes
    state = {}
    for netname in order:
        pads = [(k, v) for k, v in pad_info.items() if v[3] == netname]
        if len(pads) < 2:
            continue
        pads.sort(key=lambda kv: (kv[1][0], kv[1][1]))
        connected = set()
        for (i, j) in pad_cells[pads[0][0]]:
            for L in pads[0][1][2]:
                connected.add((i, j, L))
        state[netname] = dict(connected=connected, todo=pads[1:],
                              anchor=[pads[0][1]], done=0, total=len(pads) - 1)

    for p in range(passes):
        progress = 0
        for netname in order:
            st = state.get(netname)
            if not st or not st["todo"]:
                continue
            nid = nets[netname]
            power = netname in POWER_NETS
            cls = 1 if power else 0
            width = W_PWR if power else W_SIG
            stuck = []
            while st["todo"]:
                # prendre la pastille la plus proche d'un point deja relie
                def d2(kv):
                    x, y = kv[1][0], kv[1][1]
                    return min((x - a[0]) ** 2 + (y - a[1]) ** 2 for a in st["anchor"])
                st["todo"].sort(key=d2)
                key, info = st["todo"].pop(0)
                targets = set()
                for (i, j) in pad_cells[key]:
                    for L in info[2]:
                        targets.add((i, j, L))
                # 1er essai borne a la zone utile (beaucoup plus rapide),
                # puis 2e essai sur toute la carte si ca ne passe pas
                pts = list(st["connected"]) + list(targets)
                m = int(10.0 / GRID)
                bb = (min(p[0] for p in pts) - m, min(p[1] for p in pts) - m,
                      max(p[0] for p in pts) + m, max(p[1] for p in pts) + m)
                path = route_one(g, nid, list(st["connected"]), targets, cls, bbox=bb)
                if path is None:
                    path = route_one(g, nid, list(st["connected"]), targets, cls)
                if path is None:
                    stuck.append((key, info))
                    continue
                stamp_path(g, nid, path, (width / 2, width / 2))
                segs, vs = simplify(g, path)
                for a, b, L in segs:
                    tracks.append((a, b, L, netname, width))
                for v in vs:
                    stamp_via(g, nid, *g.cell(*v))
                    vias.append((v, netname))
                st["connected"] |= set(path)
                st["anchor"].append(info)
                st["done"] += 1
                progress += 1
            st["todo"] = stuck
        if progress == 0:
            break

    report = {n: (st["done"], st["total"]) for n, st in state.items()}
    return tracks, vias, report


def net_span(pad_info, netname):
    pts = [(v[0], v[1]) for v in pad_info.values() if v[3] == netname]
    if len(pts) < 2:
        return 0.0
    return ((max(p[0] for p in pts) - min(p[0] for p in pts)) +
            (max(p[1] for p in pts) - min(p[1] for p in pts)))


def default_order(pad_info):
    """Alimentation d'abord, USB ensuite, puis du net le plus court au plus
    long : les liaisons locales autour des boitiers a pas fin doivent prendre
    leur place avant que les bus longs ne traversent la zone."""
    head = [n for n in ("SW_NODE", "BST", "VBUS", "+5V", "VDD_AMP", "VREG_EN",
                        "USB_DP", "USB_DM", "CC1", "CC2") if n in D.NETS]
    rest = [n for n in D.NETS if n not in head and n not in PLANE_NETS]
    rest.sort(key=lambda n: net_span(pad_info, n))
    return head + rest


def attempt(g, base, nets, pad_info, pad_cells, order):
    g.restore(base)
    tracks, vias, report = route_signals(g, nets, pad_info, pad_cells, order=order)
    plane_cells = {}
    t1, v1, done, fail = stitch_planes(g, nets, pad_info, plane_cells)
    failed = [n for n, (ok, tot) in report.items() if ok < tot]
    missed = sum(tot - ok for ok, tot in report.values())
    return dict(tracks=tracks + t1, vias=vias + v1, report=report,
                failed=failed, missed=missed, stitch_done=done, stitch_fail=fail)


def main():
    import json
    g, nets, pad_info, pad_cells = build_model()
    print("grille %d x %d cellules (%.2f mm), isolation %.2f, piste %.2f" %
          (g.w, g.h, GRID, CLEAR, W_SIG))
    base = g.snapshot()

    order = default_order(pad_info)
    best = None
    for k in range(4):
        res = attempt(g, base, nets, pad_info, pad_cells, order)
        score = (res["missed"], res["stitch_fail"])
        print("passe %d : signaux manquants %d, couture ratee %d%s" %
              (k + 1, res["missed"], res["stitch_fail"],
               ("  -> " + ", ".join(res["failed"])) if res["failed"] else ""))
        if best is None or score < (best["missed"], best["stitch_fail"]):
            best = res
        if res["missed"] == 0 and res["stitch_fail"] == 0:
            break
        # rip-up : les nets en echec repassent en tete pour la tentative suivante
        order = res["failed"] + [n for n in order if n not in res["failed"]]

    tot = sum(t for _, t in best["report"].values())
    print("")
    print("RESULTAT : %d / %d liaisons de signal, %d pastilles de plan cousues (%d echecs)"
          % (tot - best["missed"], tot, best["stitch_done"], best["stitch_fail"]))
    data = {"tracks": [[list(a), list(b), L, n, w] for a, b, L, n, w in best["tracks"]],
            "vias": [[list(p), n] for p, n in best["vias"]]}
    with open(os.path.join(HW, "routes.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    print("ecrit hw/routes.json : %d pistes, %d vias" %
          (len(data["tracks"]), len(data["vias"])))


if __name__ == "__main__":
    main()
