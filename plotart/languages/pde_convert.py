"""Convert simple Processing (.pde) sketches to plotart Python.

Covers what typical sketches use: declarations, functions, for/while/if, arrays, ArrayList, PVector,
classes (fields → self.…), casts, the ternary operator, string concatenation and the event functions.
Processing's camelCase drawing functions stay as they are – plotart knows them (noFill, strokeWeight …).
Whatever cannot be converted safely is listed in the warnings; the result is checked with ast.parse.
"""
from __future__ import annotations

import ast
import re

_TOKEN = re.compile(r"""
    (?P<nl>\r?\n) | (?P<ws>[ \t\f]+) | (?P<lc>//[^\n]*) | (?P<bc>/\*.*?\*/) |
    (?P<str>"(?:\\.|[^"\\\n])*") | (?P<chr>'(?:\\.|[^'\\\n])') |
    (?P<num>0[xX][0-9a-fA-F]+[lL]? | (?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?[fFdDlL]?) |
    (?P<hex>\#[0-9a-fA-F]{6}\b) |
    (?P<id>[A-Za-z_$][\w$]*) |
    (?P<op>\+\+|--|&&|\|\||==|!=|<=|>=|\+=|-=|\*=|/=|%=|<<|>>|->|::|[{}()\[\];,.<>=+\-*/%!?:&|^~@])
    """, re.S | re.X)

BASIC = {"int": "0", "long": "0", "short": "0", "byte": "0", "float": "0.0", "double": "0.0", "boolean": "False",
         "char": '""', "String": '""', "color": "0"}
OBJECT_TYPES = {"var", "PVector", "PImage", "PFont", "PShape", "PGraphics", "ArrayList", "IntList", "FloatList",
                "StringList", "HashMap", "Integer", "Float", "Boolean", "Object", "Table", "JSONObject", "JSONArray"}
LIST_TYPES = ("ArrayList", "IntList", "FloatList", "StringList", "[]")
MODIFIERS = {"final", "static", "private", "public", "protected", "abstract", "synchronized", "transient"}
CONTROL = {"if", "else", "for", "while", "do", "switch", "try", "catch", "finally", "return", "new", "case"}
EVENTS = {"mousePressed": "mouse_pressed", "mouseReleased": "mouse_released", "mouseClicked": "mouse_clicked",
          "mouseDragged": "mouse_dragged", "mouseMoved": "mouse_moved", "mouseWheel": "mouse_wheel",
          "keyPressed": "key_pressed", "keyReleased": "key_released", "keyTyped": "key_typed"}
NAMES = {"map": "map_range", "println": "print", "pushMatrix": "push", "popMatrix": "pop", "PVector": "Vector",
         "P3D": "WEBGL", "true": "True", "false": "False", "null": "None", "this": "self",
         "mousePressed": "mouse_is_pressed", "keyPressed": "key_is_pressed", "PI": "PI"}
DROP_CALLS = {"smooth", "noSmooth", "hint", "pixelDensity", "frameRate"}
UNSUPPORTED = {"loadPixels", "updatePixels", "pixels", "tint", "noTint", "saveFrame", "save", "get", "set",
               "loadShape", "shape", "createGraphics", "loadFont", "loadStrings", "loadTable", "thread", "delay"}
INT_BUILTINS = {"width", "height", "frameCount", "mouseX", "mouseY", "pmouseX", "pmouseY", "keyCode", "millis",
                "displayWidth", "displayHeight", "second", "minute", "hour", "day", "month", "year"}
VECTOR_OPS = {"add": "+", "sub": "-", "mult": "*", "div": "/"}
VECTOR_SELF = {"normalize": "normalize", "limit": "limit", "setMag": "set_mag", "rotate": "rotate"}


class Tok:
    __slots__ = ("kind", "text", "line")

    def __init__(self, kind, text, line):
        self.kind, self.text, self.line = kind, text, line

    def __repr__(self):
        return self.text


def tokenize(src: str) -> list[Tok]:
    out, line, pos = [], 1, 0
    while pos < len(src):
        m = _TOKEN.match(src, pos)
        if not m:                                   # unknown character: keep it, the result check will notice
            out.append(Tok("op", src[pos], line))
            pos += 1
            continue
        kind, text = m.lastgroup, m.group()
        if kind != "ws":
            out.append(Tok(kind, text, line))
        line += text.count("\n")
        pos = m.end()
    return out


# ---------------------------------------------------------------------------- block structure
class Node:
    __slots__ = ("kind", "toks", "body", "text", "line")

    def __init__(self, kind, toks=None, body=None, text="", line=0):
        self.kind, self.toks, self.body, self.text, self.line = kind, toks or [], body or [], text, line


def parse(toks: list[Tok]) -> list[Node]:
    nodes, _ = _block(toks, 0)
    return nodes


def _block(toks, i):
    nodes, cur, depth, newlines = [], [], 0, 0
    while i < len(toks):
        t = toks[i]
        if t.kind == "nl":
            newlines += 1
            if not cur and newlines == 2 and nodes and nodes[-1].kind != "blank":
                nodes.append(Node("blank"))
            i += 1
            continue
        newlines = 0
        if t.kind in ("lc", "bc"):
            if not cur:
                nodes.append(Node("comment", text=t.text, line=t.line))
            i += 1
            continue
        if t.text in "([":
            depth += 1
        elif t.text in ")]":
            depth -= 1
        if t.text == "{" and depth == 0:
            prev = cur[-1].text if cur else None
            if prev in ("=", ",", "{", "return") or (prev == "]" and any(x.text == "new" for x in cur)):
                j, level = i, 0                     # array initializer: keep the braces in the statement
                while j < len(toks):
                    level += {"{": 1, "}": -1}.get(toks[j].text, 0)
                    if toks[j].kind not in ("nl", "lc", "bc"):
                        cur.append(toks[j])
                    j += 1
                    if level == 0:
                        break
                i = j
                continue
            body, i = _block(toks, i + 1)
            nodes.append(Node("block", cur, body, line=cur[0].line if cur else t.line))
            cur = []
            continue
        if t.text == "}" and depth == 0:
            if cur:
                nodes.append(Node("stmt", cur, line=cur[0].line))
            return nodes, i + 1
        if t.text == ";" and depth == 0:
            nodes.append(Node("stmt", cur, line=cur[0].line if cur else t.line))
            cur = []
            i += 1
            continue
        cur.append(t)
        i += 1
    if cur:
        nodes.append(Node("stmt", cur, line=cur[0].line))
    return nodes, i


# ---------------------------------------------------------------------------- helpers on token lists
def _texts(toks):
    return [t.text for t in toks]


def _split_top(toks, sep):
    parts, cur, depth = [], [], 0
    for t in toks:
        if t.text in "([{":
            depth += 1
        elif t.text in ")]}":
            depth -= 1
        if t.text == sep and depth == 0:
            parts.append(cur)
            cur = []
        else:
            cur.append(t)
    parts.append(cur)
    return parts


def _match(toks, i):
    """Index of the bracket closing toks[i]."""
    pairs = {"(": ")", "[": "]", "{": "}", "<": ">"}
    open_, close, depth = toks[i].text, pairs[toks[i].text], 0
    for j in range(i, len(toks)):
        if toks[j].text == open_:
            depth += 1
        elif toks[j].text == close:
            depth -= 1
            if depth == 0:
                return j
    return len(toks) - 1


def _primary_start(toks, end):
    """Start index of the primary expression ending at toks[end] (identifier with ./()/[] chain)."""
    i = end
    while i >= 0:
        t = toks[i].text
        if t in (")", "]"):
            depth = 0
            while i >= 0:
                depth += {")": 1, "]": 1, "(": -1, "[": -1}.get(toks[i].text, 0)
                if depth == 0:
                    break
                i -= 1
            i -= 1
            continue
        if toks[i].kind in ("id", "num", "str") and (i == end or toks[i + 1].text in (".", "(", "[")):
            if i > 0 and toks[i - 1].text == ".":
                i -= 2
                continue
            return i
        return i + 1
    return 0


def _primary_end(toks, i):
    """End index (exclusive) of the primary expression starting at toks[i]."""
    if i >= len(toks):
        return i
    if toks[i].text in ("-", "+", "!"):
        return _primary_end(toks, i + 1)
    if toks[i].text == "(":
        j = _match(toks, i) + 1
    else:
        j = i + 1
    while j < len(toks) and toks[j].text in (".", "(", "["):
        if toks[j].text == ".":
            j += 2
        else:
            j = _match(toks, j) + 1
    return j


class Converter:
    def __init__(self):
        self.warnings: list[str] = []
        self.globals: dict[str, str] = {}
        self.classes: dict[str, dict] = {}
        self.scope: list[dict] = []                 # local variables (name → type), innermost last
        self.cls: str | None = None                 # class whose method is being converted

    def warn(self, line, text):
        msg = f"Zeile {line}: {text}" if line else text
        if msg not in self.warnings:
            self.warnings.append(msg)

    # -------------------------------------------------------------- types and declarations
    def type_of(self, name):
        for s in reversed(self.scope):
            if name in s:
                return s[name]
        if self.cls and name in self.classes[self.cls]["fields"]:
            return self.classes[self.cls]["fields"][name]
        return self.globals.get(name)

    def decl(self, toks):
        """(type, [(name, init tokens or None)]) for a declaration, else None."""
        i = 0
        while i < len(toks) and toks[i].text in MODIFIERS:
            i += 1
        if i >= len(toks) or toks[i].kind != "id" or toks[i].text in CONTROL:
            return None
        ty = toks[i].text
        known = ty in BASIC or ty in OBJECT_TYPES or ty in self.classes or ty[:1].isupper()
        if not known:
            return None
        i += 1
        if i < len(toks) and toks[i].text == "<":
            j = _match(toks, i)
            ty += "".join(_texts(toks[i:j + 1]))
            i = j + 1
        while i + 1 < len(toks) and toks[i].text == "[" and toks[i + 1].text == "]":
            ty += "[]"
            i += 2
        if i >= len(toks) or toks[i].kind != "id":
            return None
        rest = toks[i:]
        if len(rest) > 1 and rest[1].text == "(":
            return None                             # a function, not a variable
        out = []
        for part in _split_top(rest, ","):
            if not part or part[0].kind != "id":
                return None
            name, k, arr = part[0].text, 1, ""
            while k + 1 < len(part) and part[k].text == "[" and part[k + 1].text == "]":
                arr += "[]"
                k += 2
            if k < len(part) and part[k].text == "=":
                out.append((name, ty + arr, part[k + 1:]))
            elif k == len(part):
                out.append((name, ty + arr, None))
            else:
                return None
        return out

    @staticmethod
    def default(ty):
        if ty.endswith("[]"):
            return "None"
        return BASIC.get(ty, "None")

    # -------------------------------------------------------------- expressions
    def expr(self, toks, line=0) -> str:
        if not toks:
            return ""
        toks = self._rewrite(list(toks), line)
        q = next((k for k, part in enumerate(self._depth0(toks)) if part == "?"), None)
        if q is not None:                           # c ? a : b → (a if c else b)
            depth, colon = 0, None
            for k in range(q + 1, len(toks)):
                t = toks[k].text
                depth += 1 if t in "([{?" else -1 if t in ")]}" else 0
                if t == ":" and depth == 0:
                    colon = k
                    break
                if t == ":":
                    depth += 1                      # closes a nested "?"
            if colon is not None:                   # a ternary is always the whole expression (or in parentheses)
                return (f"{self.expr(toks[q + 1:colon], line)} if {self.expr(toks[:q], line)} "
                        f"else {self.expr(toks[colon + 1:], line)}")
        parts = _split_top(toks, "+")
        if len(parts) > 1 and any(len(p) == 1 and p[0].kind == "str" for p in parts):
            return " + ".join(self._join(p, line) if (len(p) == 1 and p[0].kind == "str")
                              else f"str({self._join(p, line)})" for p in parts)
        return self._join(toks, line)

    @staticmethod
    def _depth0(toks):
        depth, out = 0, []
        for t in toks:
            out.append(t.text if depth == 0 else None)
            if t.text in "([{":
                depth += 1
            elif t.text in ")]}":
                depth -= 1
        return out

    def _rewrite(self, toks, line):
        """Token-level rewrites: new, casts, .length/.size()/.get()/…, PVector statics, array literals."""
        i = 0
        while i < len(toks):
            t = toks[i]
            nxt = toks[i + 1].text if i + 1 < len(toks) else ""
            if t.text == "new" and i + 1 < len(toks):
                toks, i = self._new(toks, i, line)
                continue
            if t.text == "{":                       # array initializer → list
                j = _match(toks, i)
                inner = [self.expr(p, line) for p in _split_top(toks[i + 1:j], ",") if p]
                toks[i:j + 1] = [Tok("py", "[" + ", ".join(inner) + "]", t.line)]
                continue
            if (t.text == "(" and i + 2 < len(toks) and toks[i + 2].text == ")" and toks[i + 1].text in BASIC
                    and i + 3 < len(toks) and (toks[i + 3].kind in ("id", "num", "py") or toks[i + 3].text == "(")):
                end = _primary_end(toks, i + 3)     # (int) x → int(x)
                fn = {"int": "int", "long": "int", "short": "int", "byte": "int", "float": "float",
                      "double": "float", "char": "chr", "String": "str", "boolean": "bool", "color": "int"}
                inner = self.expr(toks[i + 3:end], line)
                toks[i:end] = [Tok("py", f"{fn[toks[i + 1].text]}({inner})", t.line)]
                continue
            if t.text == "PVector" and nxt == "." and i + 3 < len(toks) and toks[i + 3].text == "(":
                j = _match(toks, i + 3)
                args = [self.expr(p, line) for p in _split_top(toks[i + 4:j], ",") if p]
                name = toks[i + 2].text
                py = {"fromAngle": lambda a: f"Vector.from_angle({', '.join(a)})",
                      "random2D": lambda a: "Vector.from_angle(random(TAU))",
                      "add": lambda a: f"({a[0]} + {a[1]})", "sub": lambda a: f"({a[0]} - {a[1]})",
                      "mult": lambda a: f"({a[0]} * {a[1]})", "div": lambda a: f"({a[0]} / {a[1]})",
                      "dist": lambda a: f"{a[0]}.dist({a[1]})", "dot": lambda a: f"{a[0]}.dot({a[1]})",
                      "lerp": lambda a: f"{a[0]}.lerp({a[1]}, {a[2]})"}.get(name)
                if py:
                    toks[i:j + 1] = [Tok("py", py(args), t.line)]
                    continue
                self.warn(line, f"PVector.{name}() wird nicht übertragen")
            if t.text == "." and i + 1 < len(toks) and toks[i + 1].kind == "id":
                done, toks = self._member(toks, i, line)
                if done:
                    continue
            if t.kind == "id" and t.text in UNSUPPORTED and (nxt == "(" or t.text == "pixels"):
                self.warn(line, f"{t.text}() gibt es in plotart so nicht – bitte von Hand anpassen")
            if t.text == "createFont" and nxt == "(":
                j = _match(toks, i + 1)              # createFont("Arial", 32) → "Arial"
                first = _split_top(toks[i + 2:j], ",")[0]
                toks[i:j + 1] = [Tok("py", self.expr(first, line), t.line)]
                continue
            if t.text in ("++", "--"):
                self.warn(line, f"{t.text} mitten in einem Ausdruck – bitte von Hand prüfen")
            i += 1
        return toks

    def _new(self, toks, i, line):
        name = toks[i + 1].text
        j = i + 2
        if j < len(toks) and toks[j].text == "<":
            j = _match(toks, j) + 1
        if j < len(toks) and toks[j].text == "(":
            k = _match(toks, j)
            if name in ("ArrayList", "IntList", "FloatList", "StringList"):
                py = "[]"
            elif name == "HashMap":
                py = "{}"
            else:
                args = ", ".join(self.expr(p, line) for p in _split_top(toks[j + 1:k], ",") if p)
                py = f"{NAMES.get(name, name)}({args})"
            toks[i:k + 1] = [Tok("py", py, toks[i].line)]
            return toks, i + 1
        dims, k = [], j
        while k < len(toks) and toks[k].text == "[":
            e = _match(toks, k)
            dims.append(self.expr(toks[k + 1:e], line))
            k = e + 1
        if k < len(toks) and toks[k].text == "{":
            del toks[i:k]                           # new int[] {1, 2} → the initializer alone
            return toks, i
        fill = BASIC.get(name, "None")
        py = fill
        for d in reversed([d for d in dims if d]):
            py = f"[{py}] * ({d})" if py == fill else f"[{py} for _ in range({d})]"
        toks[i:k] = [Tok("py", py, toks[i].line)]
        return toks, i + 1

    def _member(self, toks, i, line):
        """recv.length / .size() / .get(i) / .add(x) / PVector methods inside an expression."""
        name = toks[i + 1].text
        call = i + 2 < len(toks) and toks[i + 2].text == "("
        start = _primary_start(toks, i - 1)
        recv_toks = toks[start:i]
        recv = self.expr(recv_toks, line) if recv_toks else ""
        rtype = self.type_of(recv_toks[0].text) if len(recv_toks) == 1 else None
        is_list = rtype is not None and rtype.startswith(LIST_TYPES) or (rtype or "").endswith("[]")
        if name == "length" and not call:
            toks[start:i + 2] = [Tok("py", f"len({recv})", toks[i].line)]
            return True, toks
        if not call:
            return False, toks
        j = _match(toks, i + 2)
        args = [self.expr(p, line) for p in _split_top(toks[i + 3:j], ",") if p]
        py = None
        if name == "size" and not args:
            py = f"len({recv})"
        elif is_list and name == "get":
            py = f"{recv}[{args[0]}]"
        elif is_list and name == "add":
            py = f"{recv}.append({args[0]})" if len(args) == 1 else f"{recv}.insert({args[0]}, {args[1]})"
        elif is_list and name == "remove":
            py = f"{recv}.pop({args[0]})"
        elif is_list and name in ("isEmpty",):
            py = f"(len({recv}) == 0)"
        elif rtype == "PVector" and name in VECTOR_OPS:
            py = f"({recv} {VECTOR_OPS[name]} {args[0]})"
        elif rtype == "PVector" and name == "setMag":
            py = f"{recv}.set_mag({', '.join(args)})"
        elif name == "getCount" and not args:
            py = recv                               # mouseWheel(MouseEvent e): e.getCount() → the delta
        elif rtype is None and name in ("add", "get", "remove") and len(recv_toks) == 1:
            self.warn(line, f"Typ von „{recv}“ unbekannt – .{name}() bitte prüfen")
        if py is None:
            return False, toks
        toks[start:j + 1] = [Tok("py", py, toks[i].line)]
        return True, toks

    def _join(self, toks, line):
        out, k = [], 0
        while k < len(toks):
            t = toks[k]
            if t.text in ("(", "[") and t.kind == "op":     # arguments / index: each part is an expression of its own
                j = _match(toks, k)
                inner = ", ".join(self.expr(p, line) for p in _split_top(toks[k + 1:j], ",") if p)
                out.append(t.text + inner + ("]" if t.text == "[" else ")"))
                k = j + 1
                continue
            out.append(self._token(toks, k, line))
            k += 1
        return _spaced(out)

    def _token(self, toks, k, line) -> str:
        """One token in Python spelling: numbers, colours, chars, names (self., events), operators."""
        t = toks[k]
        x = t.text
        nxt = toks[k + 1].text if k + 1 < len(toks) else ""
        prv = toks[k - 1].text if k else ""
        if t.kind == "num":
            x = x.rstrip("fFdDlL") if not x.lower().startswith("0x") else x.rstrip("lL")
            if x.lower().startswith("0x") and len(x) == 10:              # 0xAARRGGBB → "#RRGGBB(AA)"
                x = f'"#{x[4:]}{x[2:4]}"' if x[2:4].lower() != "ff" else f'"#{x[4:]}"'
        elif t.kind == "hex":
            x = f'"{x}"'
        elif t.kind == "chr":
            x = '"' + x[1:-1].replace('"', '\\"') + '"'
        elif t.kind == "id":
            if prv == ".":
                x = {"setMag": "set_mag"}.get(x, x)
            elif self.cls and x in self.classes[self.cls]["fields"] and self.type_of_local(x) is None:
                x = f"self.{x}"
            elif self.cls and x in self.classes[self.cls]["methods"] and nxt == "(":
                x = f"self.{x}"
            elif x in ("mousePressed", "keyPressed") and nxt == "(":
                x = EVENTS[x]
            else:
                x = NAMES.get(x, x)
        elif x == "&&":
            x = "and"
        elif x == "||":
            x = "or"
        elif x == "!" and nxt != "=":
            x = "not"
        elif x == "/" and self._intish(toks, k - 1) and self._intish(toks, k + 1):
            x = "//"
        return x

    def type_of_local(self, name):
        for s in reversed(self.scope):
            if name in s:
                return s[name]
        return None

    def _intish(self, toks, k):
        if not 0 <= k < len(toks):
            return False
        t = toks[k]
        if t.kind == "num":
            return re.fullmatch(r"\d+", t.text) is not None
        if t.kind == "id" and t.text in INT_BUILTINS and self.type_of(t.text) is None:
            return True
        return t.kind == "id" and self.type_of(t.text) in ("int", "long", "short", "byte")

    # -------------------------------------------------------------- statements
    def stmt(self, node, out, ind):
        toks = node.toks
        line = node.line
        if not toks:
            return
        tx = _texts(toks)
        head = tx[0]
        if head in ("if", "for", "while") and "(" in tx:          # single statement without braces
            j = _match(toks, 1)
            if j + 1 < len(toks):
                self.block(Node("block", toks[:j + 1], [Node("stmt", toks[j + 1:], line=line)], line=line), out, ind)
                return
        if head == "else":
            self.block(Node("block", toks[:1] if tx[1:2] != ["if"] else toks[:_match(toks, 2) + 1],
                            [Node("stmt", toks[1:] if tx[1:2] != ["if"] else toks[_match(toks, 2) + 1:], line=line)],
                            line=line), out, ind)
            return
        if head == "return":
            out.append(ind + ("return " + self.expr(toks[1:], line)).rstrip())
            return
        if head in ("break", "continue"):
            out.append(ind + head)
            return
        if head == "super" and len(tx) > 1 and tx[1] == "(":
            out.append(ind + f"super().__init__({self.expr(toks[2:-1], line)})")
            return
        if head in DROP_CALLS and len(tx) > 1 and tx[1] == "(":
            if head == "frameRate":
                out.append(ind + f"frame_rate({self.expr(toks[2:-1], line)})")
            else:
                out.append(ind + f"# {''.join(tx)}  (in plotart nicht nötig)")
            return
        if head == "size" and len(tx) > 1 and tx[1] == "(":
            args = _split_top(toks[2:-1], ",")
            if len(args) == 3 and _texts(args[2]) in (["P3D"], ["OPENGL"]):
                out.append(ind + f"createCanvas({self.expr(args[0], line)}, {self.expr(args[1], line)}, WEBGL)")
                return
            out.append(ind + f"size({self.expr(args[0], line)}, {self.expr(args[1], line)})")
            return
        if head == "fullScreen":
            out.append(ind + "size(1920, 1080)  # fullScreen() → feste Größe")
            return
        d = self.decl(toks)
        if d is not None:
            for name, ty, init in d:
                if self.scope:                      # local variable
                    self.scope[-1][name] = ty
                else:                               # top level (static sketch), also inside loops
                    self.globals.setdefault(name, ty)
                value = self.expr(init, line) if init else self.default(ty)
                out.append(ind + f"{name} = {value}")
            return
        if len(tx) == 2 and tx[1] in ("++", "--"):
            out.append(ind + f"{self.expr(toks[:1], line)} {tx[1][0]}= 1")
            return
        if len(tx) >= 2 and tx[0] in ("++", "--"):
            out.append(ind + f"{self.expr(toks[1:], line)} {tx[0][0]}= 1")
            return
        if len(tx) >= 4 and tx[-1] == ")":
            vec = self._vector_stmt(toks, line)
            if vec:
                out.append(ind + vec)
                return
        parts = None
        for op in ("=", "+=", "-=", "*=", "/=", "%="):
            split = _split_top(toks, op)
            if len(split) == 2:
                parts = (split[0], op, split[1])
                break
        if parts:
            lhs, op, rhs = parts
            value = self.expr(rhs, line)
            if op == "/=" and self._intish(lhs, 0) and len(lhs) == 1:
                op = "//="
            out.append(ind + f"{self.expr(lhs, line)} {op} {value}")
            return
        out.append(ind + self.expr(toks, line))

    def _vector_stmt(self, toks, line):
        """v.add(w); v.normalize(); … – PVector changes itself, plotart's Vector returns a new one."""
        tx = _texts(toks)
        if "." not in tx:
            return None
        dot = len(tx) - 1 - tx[::-1].index(".")
        if dot + 2 >= len(toks) or toks[dot + 2].text != "(" or _match(toks, dot + 2) != len(toks) - 1:
            return None
        name = toks[dot + 1].text
        recv_toks = toks[:dot]
        if len(recv_toks) == 1:
            rtype = self.type_of(recv_toks[0].text)
        elif _texts(recv_toks[:2]) == ["this", "."] and len(recv_toks) == 3 and self.cls:
            rtype = self.classes[self.cls]["fields"].get(recv_toks[2].text)
        else:
            rtype = None
        if rtype != "PVector":
            return None
        recv = self.expr(recv_toks, line)
        args = [self.expr(p, line) for p in _split_top(toks[dot + 3:-1], ",") if p]
        if name in VECTOR_OPS and args:
            return f"{recv} = {recv} {VECTOR_OPS[name]} {args[0]}"
        if name in VECTOR_SELF:
            return f"{recv} = {recv}.{VECTOR_SELF[name]}({', '.join(args)})"
        if name == "set":
            return f"{recv} = Vector({', '.join(args)})"
        return None

    # -------------------------------------------------------------- blocks
    def block(self, node, out, ind):
        toks, line = node.toks, node.line
        tx = _texts(toks)
        if not tx:
            self.body(node.body, out, ind)
            return
        if tx[0] == "else" and len(tx) > 1 and tx[1] == "if":
            out.append(ind + f"elif {self.expr(toks[3:_match(toks, 2)], line)}:")
            self.body(node.body, out, ind + "    ")
            return
        if tx[0] == "else":
            out.append(ind + "else:")
            self.body(node.body, out, ind + "    ")
            return
        if tx[0] in ("if", "while"):
            out.append(ind + f"{tx[0]} {self.expr(toks[2:_match(toks, 1)], line)}:")
            self.body(node.body, out, ind + "    ")
            return
        if tx[0] == "for":
            out.append(ind + self._for(toks[2:_match(toks, 1)], line, node, out, ind))
            self.body(node.body, out, ind + "    ")       # loop variables stay in the function's scope
            return
        if tx[0] == "do":
            out.append(ind + "while True:")
            self.body(node.body, out, ind + "    ")
            node.text = "do"                        # the following "while (…);" closes it, see body()
            return
        if tx[0] in ("switch", "try"):
            self.warn(line, f"{tx[0]} wird nicht übertragen – bitte von Hand umschreiben")
            out.append(ind + f"# {tx[0]}-Block nicht übertragen")
            return
        if "class" in tx:
            self.class_def(node, out, ind)
            return
        if "(" in tx:
            self.function(node, out, ind)
            return
        self.warn(line, f"Block „{' '.join(tx)}“ nicht erkannt")
        self.body(node.body, out, ind)

    def _for(self, toks, line, node, out, ind):
        if ":" in _texts(toks):                     # for (Ball b : balls)
            k = _texts(toks).index(":")
            var = toks[k - 1].text
            self.scope_push_var(var, toks[k - 2].text if k >= 2 else None)
            return f"for {var} in {self.expr(toks[k + 1:], line)}:"
        parts = _split_top(toks, ";")
        if len(parts) == 3:
            init, cond, upd = parts
            d = self.decl(init)
            if d and len(d) == 1:
                var, _ty, start = d[0]
            elif len(init) >= 3 and init[1].text == "=":
                var, start = init[0].text, init[2:]
            else:
                var, start = None, None
            ct, ut = _texts(cond), _texts(upd)
            if var and start is not None and len(ct) >= 3 and ct[0] == var and ct[1] in ("<", "<=", ">", ">="):
                step = None
                if ut in ([var, "++"], ["++", var]):
                    step = "1"
                elif ut in ([var, "--"], ["--", var]):
                    step = "-1"
                elif len(ut) >= 3 and ut[0] == var and ut[1] in ("+=", "-="):
                    step = ("" if ut[1] == "+=" else "-") + self.expr(upd[2:], line)
                if step is not None:
                    self.scope_push_var(var, "int")
                    a, b = self.expr(start, line), self.expr(cond[2:], line)
                    if ct[1] == "<=":
                        b = f"{b} + 1"
                    elif ct[1] == ">=":
                        b = f"{b} - 1"
                    if step == "1":
                        return f"for {var} in range({a}, {b}):"
                    return f"for {var} in range({a}, {b}, {step}):"
        self.warn(line, "for-Schleife ungewöhnlich – als while-Schleife übertragen, bitte prüfen")
        if len(parts) == 3:
            init, cond, upd = parts
            if init:
                self.stmt(Node("stmt", init, line=line), out, ind)
            node.body = node.body + [Node("stmt", upd, line=line)]
            return f"while {self.expr(cond, line) or 'True'}:"
        return "while True:"

    def scope_push_var(self, name, ty):
        if self.scope:
            self.scope[-1][name] = ty

    def body(self, nodes, out, ind):
        start = len(out)
        k = 0
        while k < len(nodes):
            n = nodes[k]
            if n.kind == "comment":
                for cl in n.text.strip("/*").strip().splitlines() or [""]:
                    out.append(ind + "# " + cl.strip().lstrip("*").strip())
            elif n.kind == "blank":
                out.append("")
            elif n.kind == "stmt":
                if (k > 0 and nodes[k - 1].kind == "block" and nodes[k - 1].text == "do"
                        and _texts(n.toks)[:1] == ["while"]):
                    cond = self.expr(n.toks[2:_match(n.toks, 1)], n.line)
                    out.append(ind + "    " + f"if not ({cond}):")
                    out.append(ind + "        break")
                else:
                    self.stmt(n, out, ind)
            else:
                self.block(n, out, ind)
            k += 1
        if not any(line.strip() and not line.strip().startswith("#") for line in out[start:]):
            out.append(ind + "pass")

    # -------------------------------------------------------------- functions and classes
    def _params(self, toks):
        names = []
        for p in _split_top(toks, ","):
            ids = [t for t in p if t.kind == "id" and t.text not in MODIFIERS]
            if ids:
                ty = ids[0].text if len(ids) > 1 else None
                names.append((ids[-1].text, ty))
        return names

    def function(self, node, out, ind, method=False):
        toks = node.toks
        tx = _texts(toks)
        p = tx.index("(")
        name = tx[p - 1]
        params = self._params(toks[p + 1:_match(toks, p)])
        if name == "settings" and not method:      # Processing: size() lives in settings()
            self.scope.append({"__function__": "settings"})
            self.body(node.body, out, ind)
            self.scope.pop()
            return
        py_name = name
        if method and self.cls and name == self.cls:
            py_name = "__init__"
        elif not method:
            py_name = EVENTS.get(name, name)
        args = (["self"] if method else []) + [n for n, _ in params]
        out.append(ind + f"def {py_name}({', '.join(args)}):")
        local = {"__function__": py_name}
        local.update({n: t for n, t in params})
        self.scope.append(local)
        inner: list[str] = []
        if py_name == "__init__":
            for fname, (fty, finit) in self.classes[self.cls]["init"].items():
                value = self.expr(finit, node.line) if finit else self.default(fty)
                inner.append(ind + f"    self.{fname} = {value}")
        self.body(node.body, inner, ind + "    ")
        if not method:
            assigned = self._assigned(node.body) - set(local)
            needed = sorted(n for n in assigned if n in self.globals)
            if needed:
                out.append(ind + f"    global {', '.join(needed)}")
        out.extend(inner)
        self.scope.pop()

    def _assigned(self, nodes):
        names = set()
        for n in nodes:
            tx = _texts(n.toks) if n.kind == "stmt" else []
            if tx[:1] in (["if"], ["while"], ["for"]) and "(" in tx:     # single statement without braces
                j = _match(n.toks, 1)
                names |= self._assigned([Node("stmt", n.toks[j + 1:])])
                continue
            if tx[:1] == ["else"]:
                rest = n.toks[1:] if tx[1:2] != ["if"] else n.toks[_match(n.toks, 2) + 1:]
                names |= self._assigned([Node("stmt", rest)])
                continue
            if n.kind == "stmt" and n.toks and self.decl(n.toks) is None:
                if len(tx) >= 2 and n.toks[0].kind == "id" and tx[1] in ("=", "+=", "-=", "*=", "/=", "%=", "++", "--"):
                    names.add(tx[0])
                elif len(tx) >= 2 and tx[0] in ("++", "--"):
                    names.add(tx[1])
                elif self._vector_stmt(n.toks, 0) and n.toks[0].kind == "id":
                    names.add(tx[0])
            elif n.kind == "block":
                names |= self._assigned(n.body)
                if n.toks and n.toks[0].text == "for":
                    names |= self._assigned([Node("stmt", p) for p in _split_top(n.toks[2:-1], ";")])
        return names

    def class_def(self, node, out, ind):
        tx = _texts(node.toks)
        name = tx[tx.index("class") + 1]
        base = tx[tx.index("extends") + 1] if "extends" in tx else None
        if "interface" in tx or "abstract" in tx:
            self.warn(node.line, f"abstract/interface bei {name}: als normale Klasse übertragen")
        out.append(ind + f"class {name}{f'({base})' if base else ''}:")
        info = self.classes[name]
        outer = self.cls
        self.cls = name
        has_init = any(n.kind == "block" and _texts(n.toks)[:2] in ([name, "("],) for n in node.body)
        if not has_init:
            out.append(ind + "    def __init__(self):")
            if base:
                out.append(ind + "        super().__init__()")
            self.scope.append({"__function__": "__init__"})
            for fname, (fty, finit) in info["init"].items():
                value = self.expr(finit, node.line) if finit else self.default(fty)
                out.append(ind + f"        self.{fname} = {value}")
            self.scope.pop()
            if not info["init"] and not base:
                out.append(ind + "        pass")
            out.append("")
        for n in node.body:
            if n.kind == "block":
                self.function(n, out, ind + "    ", method=True)
                out.append("")
            elif n.kind == "comment":
                out.append(ind + "    # " + n.text.strip("/*").strip())
        self.cls = outer

    # -------------------------------------------------------------- whole sketch
    def collect(self, nodes):
        for n in nodes:
            if n.kind == "stmt":
                d = self.decl(n.toks)
                for name, ty, _init in d or []:
                    self.globals[name] = ty
            elif n.kind == "block" and "class" in _texts(n.toks):
                tx = _texts(n.toks)
                cname = tx[tx.index("class") + 1]
                fields, init, methods = {}, {}, set()
                for m in n.body:
                    if m.kind == "stmt":
                        for fname, fty, finit in self.decl(m.toks) or []:
                            fields[fname] = fty
                            init[fname] = (fty, finit)
                    elif m.kind == "block" and "(" in _texts(m.toks):
                        mt = _texts(m.toks)
                        methods.add(mt[mt.index("(") - 1])
                self.classes[cname] = {"fields": fields, "init": init, "methods": methods}

    def convert(self, source: str, title: str = "") -> dict:
        nodes = parse(tokenize(source))
        for n in nodes:                             # classes first, so their names count as types
            if n.kind == "block" and "class" in _texts(n.toks):
                tx = _texts(n.toks)
                self.classes.setdefault(tx[tx.index("class") + 1], {"fields": {}, "init": {}, "methods": set()})
        self.collect(nodes)
        out: list[str] = []
        self.body(nodes, out, "")
        code = "\n".join(_tidy(out)).strip() + "\n"
        try:
            ast.parse(code)
        except SyntaxError as exc:
            self.warn(None, f"Ergebnis noch nicht lauffähig (Python-Zeile {exc.lineno}: {exc.msg}) – bitte prüfen")
        if not title and nodes and nodes[0].kind == "comment":    # first comment line as the concept title
            title = nodes[0].text.strip("/*").strip().splitlines()[0].strip()
        title = title.replace('"""', "'''")
        head = [f'"""{title or "Aus Processing übertragen"}"""',
                "# Automatisch aus Processing (.pde) übertragen – bitte prüfen."]
        head += [f"# Hinweis – {w}" for w in self.warnings]
        return {"source": "\n".join(head) + "\n" + code, "warnings": list(self.warnings)}


_BEFORE_UNARY = {"(", "[", ",", "=", "return", "and", "or", "not", "+", "-", "*", "/", "//", "%", "<", ">", "==", "!=",
                 "<=", ">=", "if", "else", "+=", "-=", "*=", "/="}


def _spaced(parts: list[str]) -> str:
    """Join tokens with Python-like spacing: f(x), a[i], a.b, -x, but a + b."""
    out = ""
    for k, p in enumerate(parts):
        if k == 0:
            out = p
            continue
        prev = parts[k - 1]
        call_or_index = p[:1] in ("(", "[") and (prev[-1:].isalnum() or prev[-1:] in ("_", ")", "]", '"'))
        no_space_before = p in (")", "]", ",", ".", ":") or call_or_index
        unary = prev in ("-", "+") and (k < 2 or parts[k - 2] in _BEFORE_UNARY)
        no_space_after = prev in ("(", "[", ".", "~") or unary
        out += p if (no_space_before or no_space_after) else " " + p
    return out


def _tidy(lines: list[str]) -> list[str]:
    """At most one blank line in a row; two before top-level def/class (PEP 8)."""
    out: list[str] = []
    for line in lines:
        if not line.strip():
            if out and out[-1].strip():
                out.append("")
            continue
        if line.startswith(("def ", "class ")) and out and out[-1].strip():
            out.append("")
        out.append(line)
    return out


def convert_pde(source: str, title: str = "") -> dict:
    """Processing source → {"source": plotart Python, "warnings": [...]}."""
    return Converter().convert(source, title)
