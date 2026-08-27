"""Passe de finition : termine les liaisons que le routeur principal a laissees.

On repart de la grille complete (pastilles + toutes les pistes deja posees) et
on retente uniquement ce qui manque, avec une geometrie plus fine :
piste 0,127 mm et via 0,45/0,25 mm, tolerances du procede JLCPCB.

Le resultat n'est conserve que s'il ameliore le compte de liaisons restantes.
"""
import json
import os

import router as R

THIN_W = 0.127
# Vias de finition plus petits, poses uniquement par cette passe.
THIN_VIA_D, THIN_VIA_DRILL = 0.45, 0.25


def stamp_existing(g, nets, data):
    """Rejoue routes.json dans la grille."""
    for a, b, L, net, w in data["tracks"]:
        nid = nets[net]
        ci, cj = g.cell(*a)
        di, dj = g.cell(*b)
        n = max(abs(di - ci), abs(dj - cj))
        cells = [(ci + (di - ci) * t // max(1, n),
                  cj + (dj - cj) * t // max(1, n), L) for t in range(n + 1)]
        R.stamp_path(g, nid, cells, (w / 2, w / 2))
    for p, net in data["vias"]:
        # les vias deja poses sont des 0,5/0,3 : les re-empreindre a leur taille
        R.stamp_via(g, nets[net], *g.cell(*p), vd=0.5, vdrill=0.3)


def connected_cells(g, nets, data, netname):
    """Cellules du cuivre deja pose pour ce net."""
    out = set()
    for a, b, L, net, w in data["tracks"]:
        if net != netname:
            continue
        ci, cj = g.cell(*a)
        di, dj = g.cell(*b)
        n = max(abs(di - ci), abs(dj - cj))
        for t in range(n + 1):
            out.add((ci + (di - ci) * t // max(1, n),
                     cj + (dj - cj) * t // max(1, n), L))
    for p, net in data["vias"]:
        if net == netname:
            i, j = g.cell(*p)
            out.add((i, j, 0))
            out.add((i, j, 1))
    return out


def main():
    path = os.path.join(R.HW, "routes.json")
    data = json.load(open(path, encoding="utf-8"))
    before_t, before_v = len(data["tracks"]), len(data["vias"])

    # geometrie fine pour cette passe uniquement
    R.W_SIG = THIN_W
    R.VIA_D, R.VIA_DRILL = THIN_VIA_D, THIN_VIA_DRILL
    R.PLACE_HALF = (THIN_W / 2, max(R.W_PWR / 2, THIN_VIA_D / 2))

    g, nets, pad_info, pad_cells = R.build_model()
    stamp_existing(g, nets, data)

    # une pastille est "a relier" si aucune de ses cellules ne touche du
    # cuivre deja pose pour son net
    todo = []
    cache = {}
    for key, (ax, ay, layers, netname, psize) in sorted(pad_info.items()):
        if netname not in cache:
            cache[netname] = connected_cells(g, nets, data, netname)
        got = cache[netname]
        if any((i, j, L) in got for (i, j) in pad_cells[key] for L in layers):
            continue
        todo.append((key, ax, ay, layers, netname, psize))

    print("pastilles a reprendre : %d" % len(todo))
    added_t, added_v, fixed = [], [], 0
    for key, ax, ay, layers, netname, psize in todo:
        nid = nets[netname]
        cls = 0
        srcs = [(i, j, L) for (i, j) in pad_cells[key] for L in layers]
        targets = cache[netname]
        if not targets:
            continue
        path_ = R.route_one(g, nid, srcs, targets, cls)
        if path_ is None:
            print("   %-10s : toujours impossible" % ("%s.%s" % key))
            continue
        R.stamp_path(g, nid, path_, (THIN_W / 2, THIN_W / 2))
        segs, vs = R.simplify(g, path_)
        for a, b, L in segs:
            added_t.append([list(a), list(b), L, netname, THIN_W])
        for v in vs:
            R.stamp_via(g, nid, *g.cell(*v))
            added_v.append([list(v), netname])
        cache[netname] |= set(path_)
        fixed += 1
        print("   %-10s : reliee (%d segments)" % ("%s.%s" % key, len(segs)))

    if not fixed:
        print("aucune amelioration - routes.json inchange")
        return
    data["tracks"] += added_t
    data["vias"] += added_v
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    print("%d pastilles reliees ; pistes %d -> %d, vias %d -> %d"
          % (fixed, before_t, len(data["tracks"]), before_v, len(data["vias"])))


if __name__ == "__main__":
    main()
