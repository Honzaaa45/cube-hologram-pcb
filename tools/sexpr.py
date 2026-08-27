"""Minimal S-expression reader/writer for KiCad files."""

BS = chr(92)   # backslash, kept out of literals so this file stays paste-safe
QT = chr(34)   # double quote


class Sym(str):
    """A bare (unquoted) symbol token."""
    __slots__ = ()


def parse(text):
    """Parse KiCad s-expr text into nested lists. Returns list of top-level forms."""
    i, n = 0, len(text)
    stack, out = [], []
    esc = {'n': chr(10), 't': chr(9), 'r': chr(13)}
    while i < n:
        c = text[i]
        if c in ' \t\r\n':
            i += 1
        elif c == '(':
            new = []
            if stack:
                stack[-1].append(new)
            stack.append(new)
            i += 1
        elif c == ')':
            done = stack.pop()
            if not stack:
                out.append(done)
            i += 1
        elif c == QT:
            i += 1
            buf = []
            while text[i] != QT:
                if text[i] == BS:
                    nxt = text[i + 1]
                    buf.append(esc.get(nxt, nxt))
                    i += 2
                else:
                    buf.append(text[i])
                    i += 1
            i += 1
            stack[-1].append(''.join(buf))
        else:
            j = i
            while j < n and text[j] not in ' \t\r\n()' + QT:
                j += 1
            stack[-1].append(Sym(text[i:j]))
            i = j
    return out


def _esc(s):
    s = s.replace(BS, BS + BS)
    s = s.replace(QT, BS + QT)
    s = s.replace(chr(10), BS + 'n')
    return s


def _tok(x):
    return x if isinstance(x, Sym) else QT + _esc(str(x)) + QT


def dump(node, indent=0, _buf=None):
    """Serialize a nested list back to KiCad s-expr text."""
    top = _buf is None
    if top:
        _buf = []
    pad = '\t' * indent
    if not isinstance(node, list):
        _buf.append(_tok(node))
        return ''.join(_buf) if top else None

    # Forms with no nested lists stay on a single line.
    if not any(isinstance(x, list) for x in node):
        _buf.append('%s(%s)' % (pad, ' '.join(_tok(x) for x in node)))
        return ''.join(_buf) if top else None

    _buf.append('%s(%s' % (pad, _tok(node[0])))
    k = 1
    inline = []
    while k < len(node) and not isinstance(node[k], list):
        inline.append(_tok(node[k]))
        k += 1
    if inline:
        _buf.append(' ' + ' '.join(inline))
    for child in node[k:]:
        _buf.append('\n')
        dump(child, indent + 1, _buf)
    _buf.append('\n%s)' % pad)
    return ''.join(_buf) if top else None


def find(node, tag):
    """All direct children of `node` whose head is `tag`."""
    return [c for c in node if isinstance(c, list) and c and c[0] == tag]


def first(node, tag):
    r = find(node, tag)
    return r[0] if r else None


def prop(node, name, default=None):
    """Value of a (property "name" "value" ...) child."""
    for p in find(node, Sym('property')):
        if len(p) > 2 and p[1] == name:
            return p[2]
    return default
