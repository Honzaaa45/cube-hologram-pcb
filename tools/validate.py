"""Auto-verification de la conception.

Compare la netlist voulue (design.py) a ce que les librairies KiCad decrivent
reellement, et verifie que la documentation generee reste coherente avec le
schema. C'est ce script que fait tourner la CI.

    python tools/validate.py            verification complete (KiCad requis)
    python tools/validate.py --no-kicad checks purement donnees, sans KiCad

Code de sortie 1 si un controle echoue.
"""
import argparse
import collections
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D  # noqa: E402

FAILS = []
CHECKS = 0


def check(label, ok, detail=""):
    global CHECKS
    CHECKS += 1
    if ok:
        print("  ok    %s" % label)
    else:
        print("  ECHEC %s%s" % (label, (" : " + str(detail)) if detail else ""))
        FAILS.append(label)


# --------------------------------------------------------------------------
# Controles purement donnees (aucune dependance a KiCad)
# --------------------------------------------------------------------------
def data_checks():
    print("Coherence de design.py")

    refs = set(D.PARTS)
    unknown = sorted({r for conns in D.NETS.values() for r, _ in conns} - refs)
    check("toutes les references citees dans les nets existent", not unknown, unknown)

    seen = collections.Counter((r, p) for conns in D.NETS.values() for r, p in conns)
    dupes = [k for k, n in seen.items() if n > 1]
    check("aucune broche presente sur deux nets", not dupes, dupes)

    nc = set(D.NO_CONNECT)
    both = sorted(nc & set(seen))
    check("aucune broche a la fois cablee et en no-connect", not both, both)

    missing = sorted(refs - set(D.PCB_PLACE))
    check("chaque composant a un placement PCB", not missing, missing)

    extra = sorted(set(D.PCB_PLACE) - refs)
    check("aucun placement PCB orphelin", not extra, extra)

    # La documentation ne doit pas deriver du schema.
    bad = []
    for gpio, pin, net, _role in D.GPIO_MAP:
        if net in D.NETS:
            if ("U2", pin) not in set(D.NETS[net]):
                bad.append("%s/%s -> %s" % (gpio, pin, net))
    check("la table GPIO correspond a la netlist", not bad, bad)

    j2 = {p: n for p, n in D.J2_PINOUT}
    bad = []
    for pin, sig in j2.items():
        want = sig if sig in D.NETS else None
        if want is None:
            continue
        if ("J2", str(pin)) not in set(D.NETS[want]):
            bad.append("J2.%d attendu sur %s" % (pin, want))
    check("le brochage documente de J2 correspond a la netlist", not bad, bad)

    # Contrainte materielle non negociable du module N16R8.
    psram = {("U2", "28"), ("U2", "29"), ("U2", "30")}
    used = psram & set(seen)
    check("GPIO35/36/37 (PSRAM octale) laisses non connectes", not used, used)


# --------------------------------------------------------------------------
# Controles qui interrogent les librairies KiCad
# --------------------------------------------------------------------------
def kicad_checks():
    import symlib
    import fputil

    print("\nConfrontation aux librairies KiCad")

    sym_pins = {}
    missing_sym = []
    for ref, p in D.PARTS.items():
        if p["lib"] == "cube":
            sym_pins[ref] = {n for n, _, _, _ in D.CUSTOM_SYMBOLS[p["sym"]]["pins"]}
            continue
        try:
            s = symlib.get_symbol(p["lib"], p["sym"])
            sym_pins[ref] = {n for n, _, _, _ in symlib.pins(s)}
        except Exception as exc:  # symbole absent de la librairie
            missing_sym.append("%s (%s:%s) %s" % (ref, p["lib"], p["sym"], exc))
    check("tous les symboles existent", not missing_sym, missing_sym)

    bad = []
    for net, conns in D.NETS.items():
        for ref, pin in conns:
            if ref in sym_pins and pin not in sym_pins[ref]:
                bad.append("%s.%s (net %s)" % (ref, pin, net))
    check("chaque broche cablee existe sur son symbole", not bad, bad)

    netted = {(r, p) for conns in D.NETS.values() for r, p in conns}
    nc = set(D.NO_CONNECT)
    orphans = []
    for ref, pins in sym_pins.items():
        for pin in pins:
            if (ref, pin) not in netted and (ref, pin) not in nc:
                orphans.append("%s.%s" % (ref, pin))
    check("aucune broche laissee sans net ni no-connect", not orphans, sorted(orphans))

    missing_fp = [p["fp"] for p in D.PARTS.values()
                  if not symlib.footprint_exists(p["fp"])]
    check("toutes les empreintes existent", not missing_fp, sorted(set(missing_fp)))

    # Placement : rien ne doit se chevaucher ni deborder du contour.
    x0, y0 = D.BOARD_X, D.BOARD_Y
    x1, y1 = x0 + D.BOARD_W, y0 + D.BOARD_H
    boxes = {}
    for ref, (px, py, rot, _) in D.PCB_PLACE.items():
        a, b, c, d = fputil.courtyard_box(D.PARTS[ref]["fp"], rot)
        boxes[ref] = (px + a, py + b, px + c, py + d)

    over = []
    names = sorted(boxes)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = boxes[names[i]], boxes[names[j]]
            if (min(a[2], b[2]) - max(a[0], b[0]) > 0.01 and
                    min(a[3], b[3]) - max(a[1], b[1]) > 0.01):
                over.append("%s/%s" % (names[i], names[j]))
    check("aucun chevauchement de contour de courtoisie", not over, over)

    # Le connecteur USB-C deborde volontairement du bord arriere : on ne
    # verifie donc que les pastilles, qui elles doivent rester sur la carte.
    outside = []
    for ref, (px, py, rot, _) in D.PCB_PLACE.items():
        a, b, c, d = fputil.pad_box(D.PARTS[ref]["fp"], rot)
        if (px + a < x0 - 0.01 or py + b < y0 - 0.01 or
                px + c > x1 + 0.01 or py + d > y1 + 0.01):
            outside.append(ref)
    check("toutes les pastilles sont sur la carte", not outside, outside)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-kicad", action="store_true",
                    help="sauter les controles qui demandent les librairies KiCad")
    args = ap.parse_args()

    data_checks()
    if args.no_kicad:
        print("\n(controles KiCad sautes)")
    else:
        try:
            kicad_checks()
        except RuntimeError as exc:
            print("\nKiCad introuvable : %s" % exc)
            print("Relancez avec --no-kicad pour ne faire que les controles donnees.")
            return 2

    print("\n%d controles, %d echec(s)" % (CHECKS, len(FAILS)))
    if FAILS:
        for f in FAILS:
            print("  - %s" % f)
        return 1
    print("Conception coherente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
