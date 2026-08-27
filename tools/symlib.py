"""Load KiCad symbol libraries: resolve `extends`, expose pins and sub-units."""
import os
import kicadpath
import sexpr
from sexpr import Sym, find, first

KICAD_SHARE = kicadpath.share_dir()
SYM_DIR = os.path.join(KICAD_SHARE, "symbols")
FP_DIR = os.path.join(KICAD_SHARE, "footprints")

_cache = {}


def load_lib(libname):
    if libname in _cache:
        return _cache[libname]
    path = os.path.join(SYM_DIR, libname + ".kicad_sym")
    with open(path, encoding="utf-8") as fh:
        root = sexpr.parse(fh.read())[0]
    syms = {}
    for s in find(root, Sym("symbol")):
        syms[s[1]] = s
    _cache[libname] = syms
    return syms


def get_symbol(libname, name):
    """Return the symbol node, with `extends` resolved into a standalone definition."""
    syms = load_lib(libname)
    if name not in syms:
        raise KeyError("%s not in %s" % (name, libname))
    node = syms[name]
    ext = first(node, Sym("extends"))
    if not ext:
        return node
    parent = get_symbol(libname, ext[1])
    # Child keeps its own properties; inherits parent's graphic/pin sub-units.
    merged = [Sym("symbol"), name]
    for c in node[2:]:
        if isinstance(c, list) and c[0] in (Sym("extends"),):
            continue
        merged.append(c)
    own_props = {p[1] for p in find(node, Sym("property"))}
    for c in parent[2:]:
        if isinstance(c, list) and c[0] == Sym("property") and c[1] in own_props:
            continue
        if isinstance(c, list) and c[0] == Sym("symbol"):
            # rename child unit: Parent_1_1 -> Child_1_1
            unit = list(c)
            unit[1] = name + c[1][len(parent[1]):]
            merged.append(unit)
        elif isinstance(c, list) and c[0] != Sym("extends"):
            merged.append(c)
    return merged


def units(sym):
    """Sub-symbol nodes (the graphic/pin units)."""
    return find(sym, Sym("symbol"))


def pins(sym):
    """[(number, name, etype, unit_index)] across all units."""
    out = []
    for u in units(sym):
        # name is like "FOO_1_1" -> unit index 1
        tail = u[1].rsplit("_", 2)
        uidx = int(tail[-2]) if len(tail) == 3 and tail[-2].isdigit() else 0
        for p in find(u, Sym("pin")):
            etype = str(p[1])
            num = first(p, Sym("number"))[1]
            nm = first(p, Sym("name"))[1]
            out.append((num, nm, etype, uidx))

    def key(t):
        try:
            return (0, int(t[0]), "")
        except ValueError:
            return (1, 0, t[0])

    return sorted(out, key=key)


def unit_count(sym):
    return max([p[3] for p in pins(sym)] or [1])


def footprint_exists(fp):
    lib, name = fp.split(":", 1)
    return os.path.isfile(os.path.join(FP_DIR, lib + ".pretty", name + ".kicad_mod"))


def load_footprint(fp):
    lib, name = fp.split(":", 1)
    path = os.path.join(FP_DIR, lib + ".pretty", name + ".kicad_mod")
    with open(path, encoding="utf-8") as fh:
        return sexpr.parse(fh.read())[0]


if __name__ == "__main__":
    import sys
    lib, name = sys.argv[1], sys.argv[2]
    s = get_symbol(lib, name)
    print("### %s:%s  (units=%d)" % (lib, name, unit_count(s)))
    for num, nm, et, u in pins(s):
        print("  u%d  %-4s %-22s %s" % (u, num, nm, et))
