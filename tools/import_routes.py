"""Capture le routage present dans hw/cube.kicad_pcb vers hw/routes.json.

Le pipeline regenere le PCB depuis design.py + routes.json. Toute piste tracee
a la main dans Pcbnew serait donc perdue a la prochaine generation. Ce script
ferme la boucle : on relit le cuivre du PCB et on le remet dans routes.json,
qui redevient la source du routage.

    python tools/import_routes.py                garde tout
    python tools/import_routes.py --drop-dangling  retire les moignons que le
                                                   DRC signale comme non relies

Le format de routes.json accepte le nom de couche ("F.Cu", "In2.Cu"...) et,
pour un via, sa taille et son percage reels.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sexpr  # noqa: E402
from sexpr import Sym, find, first  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, "hw", "cube.kicad_pcb")
OUT = os.path.join(ROOT, "hw", "routes.json")
DRC = os.path.join(ROOT, "hw", "drc.rpt")


def dangling_points():
    """Coordonnees des pistes que le DRC declare non reliees a une extremite."""
    if not os.path.isfile(DRC):
        return set()
    pts = set()
    keep = False
    for line in open(DRC, encoding="utf-8", errors="replace"):
        if line.startswith("["):
            keep = "track_dangling" in line
            continue
        if keep:
            m = re.search(r"@\(([\d,.]+) mm, ([\d,.]+) mm\)", line)
            if m:
                pts.add((round(float(m.group(1).replace(",", ".")), 4),
                         round(float(m.group(2).replace(",", ".")), 4)))
    return pts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--drop-dangling", action="store_true",
                    help="retirer les pistes signalees non reliees par le DRC")
    args = ap.parse_args()

    root = sexpr.parse(open(PCB, encoding="utf-8").read())[0]
    nets = {int(n[1]): n[2] for n in find(root, Sym("net"))}

    drop = dangling_points() if args.drop_dangling else set()
    tracks, vias, dropped = [], [], 0

    for s in find(root, Sym("segment")):
        a = first(s, Sym("start"))
        b = first(s, Sym("end"))
        p1 = (float(a[1]), float(a[2]))
        p2 = (float(b[1]), float(b[2]))
        net = nets.get(int(first(s, Sym("net"))[1]), "")
        if not net:
            continue
        if drop and (round(p1[0], 4), round(p1[1], 4)) in drop:
            dropped += 1
            continue
        tracks.append([list(p1), list(p2),
                       str(first(s, Sym("layer"))[1]),
                       net.lstrip("/"),
                       float(first(s, Sym("width"))[1])])

    for v in find(root, Sym("via")):
        at = first(v, Sym("at"))
        net = nets.get(int(first(v, Sym("net"))[1]), "")
        if not net:
            continue
        vias.append([[float(at[1]), float(at[2])], net.lstrip("/"),
                     float(first(v, Sym("size"))[1]),
                     float(first(v, Sym("drill"))[1])])

    layers = sorted({t[2] for t in tracks})
    widths = sorted({t[4] for t in tracks})
    sizes = sorted({(v[2], v[3]) for v in vias})
    print("pistes  : %d  (couches %s)" % (len(tracks), ", ".join(layers)))
    print("          largeurs %s" % ", ".join("%g" % w for w in widths))
    print("vias    : %d  (%s)" % (len(vias), ", ".join("%g/%g" % s for s in sizes)))
    if dropped:
        print("retires : %d moignon(s) signale(s) par le DRC" % dropped)

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"tracks": tracks, "vias": vias}, fh)
    print("ecrit hw/routes.json (%.0f Ko)" % (os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
