"""Genere hw/cube.kicad_pcb : empilage 4 couches, empreintes placees, nets
affectes, contour de carte, plans de masse/alimentation et serigraphie."""
import math
import os
import uuid as _uuid

import sexpr
import symlib
import fputil
import design as D
from sexpr import Sym, first

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(os.path.dirname(HERE), "hw")

# KiCad 9 : F.Cu=0, B.Cu=2, In1.Cu=4, In2.Cu=6
LAYERS = [
    (0, "F.Cu", "signal", None),
    (4, "In1.Cu", "signal", None),   # plan de masse (voir docs/CARTE.md)
    (6, "In2.Cu", "signal", None),   # plan +3V3
    (2, "B.Cu", "signal", None),
    (9, "F.Adhes", "user", "F.Adhesive"), (11, "B.Adhes", "user", "B.Adhesive"),
    (13, "F.Paste", "user", None), (15, "B.Paste", "user", None),
    (5, "F.SilkS", "user", "F.Silkscreen"), (7, "B.SilkS", "user", "B.Silkscreen"),
    (1, "F.Mask", "user", None), (3, "B.Mask", "user", None),
    (17, "Dwgs.User", "user", "User.Drawings"), (19, "Cmts.User", "user", "User.Comments"),
    (21, "Eco1.User", "user", "User.Eco1"), (23, "Eco2.User", "user", "User.Eco2"),
    (25, "Edge.Cuts", "user", None), (27, "Margin", "user", None),
    (31, "F.CrtYd", "user", "F.Courtyard"), (29, "B.CrtYd", "user", "B.Courtyard"),
    (35, "F.Fab", "user", None), (33, "B.Fab", "user", None),
]

_seen = {}


def uid(key):
    if key not in _seen:
        _seen[key] = str(_uuid.uuid5(_uuid.NAMESPACE_URL, "cube-pcb/" + key))
    return _seen[key]


def N(v):
    return Sym(("%.6f" % v).rstrip("0").rstrip(".") if isinstance(v, float) else str(v))


def xy(x, y):
    return [Sym("xy"), N(x), N(y)]


# Les etiquettes locales du schema sont exportees par KiCad avec le prefixe de
# feuille "/". Les symboles d'alimentation, eux, sont globaux et n'en ont pas.
# On reproduit exactement cette convention pour que "Update PCB from schematic"
# ne renomme rien.
GLOBAL_NETS = {"GND", "+3V3", "+5V"}


def disp(name):
    if not name:
        return ""
    return name if name in GLOBAL_NETS else "/" + name


def net_table():
    """nom de net -> index. 0 est reserve aux pastilles non connectees."""
    nets = {"": 0}
    for i, name in enumerate(sorted(D.NETS), start=1):
        nets[name] = i
    return nets


def pad_net_map():
    """(ref, numero_pastille) -> nom de net."""
    m = {}
    for name, conns in D.NETS.items():
        for ref, pin in conns:
            m[(ref, pin)] = name
    return m


# --------------------------------------------------------------------------
# Empreintes
# --------------------------------------------------------------------------
SKIP_TOP = {Sym("version"), Sym("generator"), Sym("generator_version"),
            Sym("layer"), Sym("property"), Sym("at"), Sym("uuid"), Sym("path")}


SILK_SIZE = 0.6
SILK_THICK = 0.09


def place_silk():
    """Position de chaque reference sur la serigraphie, sans chevauchement.

    On essaie quatre cotes autour du contour de courtoisie ; si aucun ne tient,
    la reference est masquee sur la serigraphie (elle reste sur F.Fab, donc
    lisible sur le plan d'implantation).
    """
    boxes = {}
    for ref in D.PARTS:
        x, y, rot, _ = D.PCB_PLACE[ref]
        a, b, c, d = fputil.courtyard_box(D.PARTS[ref]["fp"], rot)
        boxes[ref] = (x + a, y + b, x + c, y + d)

    def hits(box, skip):
        for r, bb in boxes.items():
            if r == skip:
                continue
            if (box[0] < bb[2] and box[2] > bb[0] and
                    box[1] < bb[3] and box[3] > bb[1]):
                return True
        for bb in placed:
            if (box[0] < bb[2] and box[2] > bb[0] and
                    box[1] < bb[3] and box[3] > bb[1]):
                return True
        return False

    placed = []
    out = {}
    # les gros boitiers passent en premier : leur etiquette a la priorite
    order = sorted(D.PARTS, key=lambda r: -((boxes[r][2] - boxes[r][0]) *
                                            (boxes[r][3] - boxes[r][1])))
    for ref in order:
        x, y, rot, _ = D.PCB_PLACE[ref]
        b = boxes[ref]
        tw = len(ref) * SILK_SIZE * 0.78 + 0.2
        th = SILK_SIZE + 0.2
        cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
        cands = [(cx, b[1] - th / 2 - 0.1), (cx, b[3] + th / 2 + 0.1),
                 (b[2] + tw / 2 + 0.1, cy), (b[0] - tw / 2 - 0.1, cy)]
        chosen = None
        for px, py in cands:
            box = (px - tw / 2, py - th / 2, px + tw / 2, py + th / 2)
            # le texte doit tenir entierement sur la carte, sinon il est rogne
            if (box[0] < D.BOARD_X + 0.2 or box[1] < D.BOARD_Y + 0.2 or
                    box[2] > D.BOARD_X + D.BOARD_W - 0.2 or
                    box[3] > D.BOARD_Y + D.BOARD_H - 0.2):
                continue
            if not hits(box, ref):
                chosen = (px - x, py - y)
                placed.append(box)
                break
        out[ref] = chosen
    return out


SILK_POS = None


def build_footprint(ref, part, x, y, rot, nets, padmap):
    src = symlib.load_footprint(part["fp"])
    fp = [Sym("footprint"), part["fp"],
          [Sym("layer"), "F.Cu"],
          [Sym("uuid"), uid("fp-" + ref)],
          [Sym("at"), N(x), N(y)] + ([N(rot)] if rot else [])]

    descr = first(src, Sym("descr"))
    tags = first(src, Sym("tags"))
    if descr:
        fp.append(descr)
    if tags:
        fp.append(tags)

    def txt_prop(name, value, ly, dy, hide=False, dx=0.0):
        p = [Sym("property"), name, value,
             [Sym("at"), N(dx), N(dy), N(0)],
             [Sym("unlocked"), Sym("yes")],
             [Sym("layer"), ly],
             ([Sym("hide"), Sym("yes")] if hide else None),
             [Sym("uuid"), uid("fpp-%s-%s" % (ref, name))],
             [Sym("effects"), [Sym("font"),
                               [Sym("size"), N(SILK_SIZE), N(SILK_SIZE)],
                               [Sym("thickness"), N(SILK_THICK)]]]]
        return [e for e in p if e is not None]

    b = fputil.courtyard_box(part["fp"], rot)
    sp = (SILK_POS or {}).get(ref)
    if sp:
        fp.append(txt_prop("Reference", ref, "F.SilkS", sp[1], dx=sp[0]))
    else:
        # aucune place libre : la reference reste sur F.Fab (plan d'implantation)
        fp.append(txt_prop("Reference", ref, "F.SilkS", b[1] - 0.7, hide=True))
    fp.append(txt_prop("Value", part["val"], "F.Fab", b[3] + 0.7, hide=True))
    fp.append(txt_prop("Footprint", part["fp"], "F.Fab", 0, hide=True))
    fp.append(txt_prop("Datasheet", "", "F.Fab", 0, hide=True))
    fp.append(txt_prop("Description", part["desc"], "F.Fab", 0, hide=True))

    attr = first(src, Sym("attr"))
    if attr:
        fp.append(attr)
    if part["dnp"]:
        fp.append([Sym("attr"), Sym("dnp")])

    pad_i = 0
    for node in src[2:]:
        if not isinstance(node, list) or node[0] in SKIP_TOP:
            continue
        if node[0] == Sym("attr"):
            continue
        if node[0] == Sym("pad"):
            pad_i += 1
            pad = [c for c in node if not (isinstance(c, list)
                                           and c[0] in (Sym("uuid"), Sym("net")))]
            # l'angle de pastille est absolu dans un .kicad_pcb
            at = first(pad, Sym("at"))
            local_a = float(at[3]) if len(at) > 3 else 0.0
            newa = (local_a + rot) % 360.0
            at_new = [Sym("at"), N(float(at[1])), N(float(at[2]))]
            if newa:
                at_new.append(N(newa))
            pad = [at_new if (isinstance(c, list) and c[0] == Sym("at")) else c for c in pad]

            netname = padmap.get((ref, str(node[1])))
            out = [Sym("pad")]
            for c in pad[1:]:
                out.append(c)
            if netname:
                out.append([Sym("net"), N(nets[netname]), disp(netname)])
            out.append([Sym("uuid"), uid("pad-%s-%s-%d" % (ref, node[1], pad_i))])
            fp.append(out)
        else:
            fp.append(node)
    return fp


# --------------------------------------------------------------------------
# Graphiques
# --------------------------------------------------------------------------
def gr_line(p1, p2, layer, width, key):
    return [Sym("gr_line"),
            [Sym("start"), N(p1[0]), N(p1[1])],
            [Sym("end"), N(p2[0]), N(p2[1])],
            [Sym("stroke"), [Sym("width"), N(width)], [Sym("type"), Sym("default")]],
            [Sym("layer"), layer], [Sym("uuid"), uid(key)]]


def gr_arc(s, m, e, layer, width, key):
    return [Sym("gr_arc"),
            [Sym("start"), N(s[0]), N(s[1])],
            [Sym("mid"), N(m[0]), N(m[1])],
            [Sym("end"), N(e[0]), N(e[1])],
            [Sym("stroke"), [Sym("width"), N(width)], [Sym("type"), Sym("default")]],
            [Sym("layer"), layer], [Sym("uuid"), uid(key)]]


def gr_text(txt, x, y, layer, size, key, rot=0, mirror=False, thick=0.15):
    eff = [Sym("effects"), [Sym("font"), [Sym("size"), N(size), N(size)],
                            [Sym("thickness"), N(thick)]]]
    if mirror:
        eff.append([Sym("justify"), Sym("mirror")])
    return [Sym("gr_text"), txt,
            [Sym("at"), N(x), N(y)] + ([N(rot)] if rot else []),
            [Sym("layer"), layer], [Sym("uuid"), uid(key)], eff]


def board_outline():
    """Rectangle a coins arrondis sur Edge.Cuts."""
    x0, y0 = D.BOARD_X, D.BOARD_Y
    x1, y1 = D.BOARD_X + D.BOARD_W, D.BOARD_Y + D.BOARD_H
    r = D.BOARD_CORNER_R
    w = 0.1
    out = [
        gr_line((x0 + r, y0), (x1 - r, y0), "Edge.Cuts", w, "edge-n"),
        gr_line((x1, y0 + r), (x1, y1 - r), "Edge.Cuts", w, "edge-e"),
        gr_line((x1 - r, y1), (x0 + r, y1), "Edge.Cuts", w, "edge-s"),
        gr_line((x0, y1 - r), (x0, y0 + r), "Edge.Cuts", w, "edge-o"),
    ]
    k = r * (1 - math.sqrt(0.5))
    corners = [
        ((x1 - r, y0), (x1 - k, y0 + k), (x1, y0 + r), "ne"),
        ((x1, y1 - r), (x1 - k, y1 - k), (x1 - r, y1), "se"),
        ((x0 + r, y1), (x0 + k, y1 - k), (x0, y1 - r), "so"),
        ((x0, y0 + r), (x0 + k, y0 + k), (x0 + r, y0), "no"),
    ]
    for s, m, e, tag in corners:
        out.append(gr_arc(s, m, e, "Edge.Cuts", w, "edge-arc-" + tag))
    return out


def zone(net_idx, net_name, layers, poly, key, priority=0, name=""):
    z = [Sym("zone"),
         [Sym("net"), N(net_idx)],
         [Sym("net_name"), net_name],
         [Sym("layers")] + list(layers),
         [Sym("uuid"), uid(key)]]
    if name:
        z.append([Sym("name"), name])
    z.append([Sym("hatch"), Sym("edge"), N(0.5)])
    if priority:
        z.append([Sym("priority"), N(priority)])
    z += [[Sym("connect_pads"), [Sym("clearance"), N(0.2)]],
          [Sym("min_thickness"), N(0.2)],
          [Sym("filled_areas_thickness"), Sym("no")],
          [Sym("fill"), Sym("yes"),
           [Sym("thermal_gap"), N(0.3)],
           [Sym("thermal_bridge_width"), N(0.4)],
           # 0 = supprimer les ilots non relies : evite des zones orphelines
           [Sym("island_removal_mode"), N(0)]],
          [Sym("polygon"), [Sym("pts")] + [xy(px, py) for px, py in poly]]]
    return z


def build():
    nets = net_table()
    padmap = pad_net_map()

    pcb = [Sym("kicad_pcb"),
           [Sym("version"), Sym("20241229")],
           [Sym("generator"), "pcbnew"],
           [Sym("generator_version"), "9.0"],
           [Sym("general"), [Sym("thickness"), N(1.6)],
            [Sym("legacy_teardrops"), Sym("no")]],
           [Sym("paper"), "A4"],
           [Sym("title_block"),
            [Sym("title"), D.TITLE],
            [Sym("rev"), D.REV],
            [Sym("comment"), Sym("1"), "48 x 52 mm - 4 couches - F.Cu / GND / PWR / B.Cu"]]]

    lay = [Sym("layers")]
    for num, nm, typ, usr in LAYERS:
        e = [N(num), nm, Sym(typ)]
        if usr:
            e.append(usr)
        lay.append(e)
    pcb.append(lay)

    pcb.append([Sym("setup"),
                [Sym("pad_to_mask_clearance"), N(0.05)],
                [Sym("aux_axis_origin"), N(D.BOARD_X), N(D.BOARD_Y + D.BOARD_H)],
                [Sym("allow_soldermask_bridges_in_footprints"), Sym("no")],
                [Sym("tenting"), Sym("front"), Sym("back")]])

    for name, idx in sorted(nets.items(), key=lambda kv: kv[1]):
        pcb.append([Sym("net"), N(idx), disp(name)])

    global SILK_POS
    SILK_POS = place_silk()
    for ref, part in D.PARTS.items():
        x, y, rot, _ = D.PCB_PLACE[ref]
        pcb.append(build_footprint(ref, part, x, y, rot, nets, padmap))

    pcb.extend(board_outline())

    # ---- plans de cuivre ----
    m = 0.3
    x0, y0 = D.BOARD_X + m, D.BOARD_Y + m
    x1, y1 = D.BOARD_X + D.BOARD_W - m, D.BOARD_Y + D.BOARD_H - m
    full = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    pcb.append(zone(nets["GND"], disp("GND"), ["In1.Cu"], full, "z-gnd-in1",
                    name="Plan de masse"))
    pcb.append(zone(nets["+3V3"], disp("+3V3"), ["In2.Cu"], full, "z-3v3-in2",
                    name="Plan +3V3"))
    pcb.append(zone(nets["GND"], disp("GND"), ["F.Cu"], full, "z-gnd-f",
                    name="Remplissage masse dessus"))
    pcb.append(zone(nets["GND"], disp("GND"), ["B.Cu"], full, "z-gnd-b",
                    name="Remplissage masse dessous"))

    # ---- serigraphie ----
    cx = D.BOARD_X + D.BOARD_W / 2
    # au-dessus de l'empreinte USB-C, sinon le texte est traverse par ses trous
    pcb.append(gr_text("CUBE  rev %s" % D.REV, cx, D.BOARD_Y + D.BOARD_H - 12.5,
                       "B.SilkS", 1.4, "silk-title", mirror=True))
    pcb.append(gr_text("GPIO35-37 = PSRAM : NE PAS UTILISER",
                       cx, D.BOARD_Y + D.BOARD_H - 10.6,
                       "B.SilkS", 0.7, "silk-warn", mirror=True))
    # brochage du connecteur ecran, au dos
    jx, jy, _, _ = D.PCB_PLACE["J2"]
    for i, (pin, sig) in enumerate(D.J2_PINOUT):
        col, row = divmod(i, 7)
        pcb.append(gr_text("%d %s" % (pin, sig),
                           jx - 12 + col * 13, jy + 8 + row * 1.6,
                           "B.SilkS", 0.6, "silk-j2-%d" % pin, mirror=True, thick=0.1))
    pcb.append(gr_text("microSD", 103.0, 117.0, "F.SilkS", 0.7, "silk-sd"))
    pcb.append(gr_text("USB-C", cx, 143.0, "F.SilkS", 0.7, "silk-usb"))

    pcb.extend(routing(nets))
    pcb.append([Sym("embedded_fonts"), Sym("no")])
    return pcb


def routing(nets):
    """Pistes et vias produits par router.py, s'ils existent."""
    import json
    path = os.path.join(OUT_DIR, "routes.json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    lname = {0: "F.Cu", 1: "B.Cu"}
    out = []
    for i, (a, b, L, net, w) in enumerate(data["tracks"]):
        out.append([Sym("segment"),
                    [Sym("start"), N(a[0]), N(a[1])],
                    [Sym("end"), N(b[0]), N(b[1])],
                    [Sym("width"), N(w)],
                    [Sym("layer"), lname[L]],
                    [Sym("net"), N(nets[net])],
                    [Sym("uuid"), uid("seg-%d" % i)]])
    for i, (p, net) in enumerate(data["vias"]):
        out.append([Sym("via"),
                    [Sym("at"), N(p[0]), N(p[1])],
                    [Sym("size"), N(0.5)],
                    [Sym("drill"), N(0.3)],
                    [Sym("layers"), "F.Cu", "B.Cu"],
                    [Sym("net"), N(nets[net])],
                    [Sym("uuid"), uid("via-%d" % i)]])
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    pcb = build()
    path = os.path.join(OUT_DIR, D.PROJECT + ".kicad_pcb")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(sexpr.dump(pcb) + "\n")
    print("ecrit %s  (%d octets)" % (path, os.path.getsize(path)))


if __name__ == "__main__":
    main()
