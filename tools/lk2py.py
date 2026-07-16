#!/usr/bin/env python3
"""LeekScript (.lk) -> Python transpiler for the V8 AI.

Targets the LeekWars polyglot runtime (GraalPy guest): flat game API and
CHIP_*/WEAPON_*/EFFECT_* constants are injected into the global scope, the
source is evaluated once per fight, then turn() is re-invoked every turn.

Not a general LeekScript compiler — it covers the constructs used by
V8_modules (see POLYGLOT_PORTING_GUIDE.md in the generator repo for the
runtime semantics this encodes):
  - `+`  -> lw_add()   (LS null->0 coercion, auto string coercion)
  - `%`  -> lw_mod()   (Java remainder sign, not Python floor-mod)
  - subscript loads -> lw_get() (missing key / OOB -> None, like LS)
  - foreach iterates VALUES for both arrays and maps -> lw_values()
  - C-style for -> while with increment duplicated before `continue`
  - inline `function(a,b){...}` closures hoisted to named defs
  - `global x = v` initializes once (module level); functions that assign
    a declared global get a `global` statement
  - class instance fields -> __init__ assignments (never shared class attrs)

Usage:
  python3 tools/lk2py.py                # transpile V8_modules -> V8_python/main.py
  python3 tools/lk2py.py --check        # transpile + CPython syntax check
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / "V8_modules"
OUT_FILE = REPO / "V8_python" / "main.py"
PRELUDE_FILE = REPO / "tools" / "lw_prelude.py"

PY_KEYWORDS = {
    "False", "None", "True", "and", "as", "assert", "async", "await",
    "break", "class", "continue", "def", "del", "elif", "else", "except",
    "finally", "for", "from", "global", "if", "import", "in", "is",
    "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try",
    "while", "with", "yield",
}

# LS keywords that survive into Python with the same meaning
LS_KEYWORDS = {"if", "else", "while", "for", "return", "break", "continue",
               "var", "global", "function", "class", "extends", "constructor",
               "static", "new", "null", "true", "false", "in", "instanceof",
               "include", "and", "or", "not"}


# ─────────────────────────── Lexer ───────────────────────────

TOKEN_RE = re.compile(r"""
    (?P<ws>[ \t]+)
  | (?P<nl>\r?\n)
  | (?P<lcomment>//[^\n]*)
  | (?P<bcomment>/\*.*?\*/)
  | (?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
  | (?P<number>0x[0-9a-fA-F]+|\d+\.\d+|\.\d+|\d+)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>===|!==|<<=|>>=|\*\*|\+\+|--|&&|\|\||==|!=|<=|>=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|=>|[-+*/%=<>!&|^~?:;,.(){}\[\]\\@])
""", re.VERBOSE | re.DOTALL)


class Tok:
    __slots__ = ("kind", "text", "line")

    def __init__(self, kind, text, line):
        self.kind = kind
        self.text = text
        self.line = line

    def __repr__(self):
        return f"Tok({self.kind},{self.text!r},L{self.line})"


def lex(source, filename="?"):
    toks = []
    pos = 0
    line = 1
    n = len(source)
    while pos < n:
        m = TOKEN_RE.match(source, pos)
        if not m:
            raise SyntaxError(f"{filename}:{line}: cannot lex at {source[pos:pos+40]!r}")
        kind = m.lastgroup
        text = m.group()
        if kind == "nl":
            line += 1
        elif kind in ("ws", "lcomment"):
            pass
        elif kind == "bcomment":
            line += text.count("\n")
        else:
            toks.append(Tok(kind, text, line))
        pos = m.end()
    toks.append(Tok("eof", "", line))
    return toks


# ─────────────────────────── Parser / Emitter ───────────────────────────

class Fn:
    """Per-function context: local names + whether globals get assigned."""

    def __init__(self):
        self.locals = set()          # var-declared names, params, loop vars
        self.assigned = set()        # bare names assigned anywhere
        self.hoisted = []            # hoisted closure defs (list of line lists)
        self.hoist_counter = 0


class Transpiler:
    def __init__(self, global_names):
        self.global_names = global_names   # all `global x` names across files
        self.out = []                      # emitted lines (module level)
        self.toplevel_stmts = []           # per-turn statements (into turn())
        self.fn_stack = []
        self.loop_stack = []               # for continue-in-C-for handling
        self.class_stack = []              # class names, for static refs
        self.class_statics = {}            # class name -> (base, {static names})
        self.class_methods = {}            # class name -> (base, {method names})
        self.cur_statics = set()           # statics of the class being compiled
        self.cur_methods = set()           # instance methods (incl. inherited)
        self.in_static_method = False
        self.cur_class = None
        self.filename = "?"

    # ── token stream helpers ──
    def load(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self, k=0):
        return self.toks[min(self.i + k, len(self.toks) - 1)]

    def next(self):
        t = self.toks[self.i]
        if self.i < len(self.toks) - 1:
            self.i += 1
        return t

    def at(self, text):
        return self.peek().text == text

    def accept(self, text):
        if self.at(text):
            return self.next()
        return None

    def expect(self, text):
        t = self.next()
        if t.text != text:
            raise SyntaxError(f"{self.filename}:{t.line}: expected {text!r}, got {t.text!r}")
        return t

    def skip_semis(self):
        while self.at(";"):
            self.next()

    # ── identifier emission ──
    def ident(self, name):
        if name in PY_KEYWORDS:
            return name + "_"
        # Python mangles __name inside class bodies (-> _Class__name), which
        # breaks LS double-underscore globals referenced from methods
        if name.startswith("__") and not name.endswith("__"):
            return "lw" + name
        return name

    # ── expression parsing (precedence climbing) ──
    # returns Python source string
    BINOPS = [
        ("||",),
        ("&&",),
        ("|",),
        ("^",),
        ("&",),
        ("==", "!=", "===", "!=="),
        ("<", ">", "<=", ">=", "instanceof"),
        ("<<", ">>"),
        ("+", "-"),
        ("*", "/", "%"),
    ]

    def parse_expression(self):
        return self.parse_ternary()

    def parse_ternary(self):
        cond = self.parse_binary(0)
        if self.at("?"):
            self.next()
            then = self.parse_ternary()
            self.expect(":")
            other = self.parse_ternary()
            return f"({then} if {cond} else {other})"
        return cond

    def parse_binary(self, level):
        if level >= len(self.BINOPS):
            return self.parse_unary()
        ops = self.BINOPS[level]
        left = self.parse_binary(level + 1)
        while self.peek().text in ops:
            op = self.next().text
            right = self.parse_binary(level + 1)
            left = self.emit_binop(op, left, right)
        return left

    def emit_binop(self, op, a, b):
        if op == "||":
            return f"({a} or {b})"
        if op == "&&":
            return f"({a} and {b})"
        if op in ("==", "==="):
            return f"({a} == {b})"
        if op in ("!=", "!=="):
            return f"({a} != {b})"
        if op == "+":
            return f"lw_add({a}, {b})"
        if op == "%":
            return f"lw_mod({a}, {b})"
        if op == "/":
            return f"lw_div({a}, {b})"
        if op == "-":
            return f"lw_sub({a}, {b})"
        if op == "*":
            return f"lw_mul({a}, {b})"
        if op == "instanceof":
            return f"isinstance({a}, {b})"
        return f"({a} {op} {b})"

    def parse_unary(self):
        t = self.peek()
        if t.text == "!":
            self.next()
            return f"(not {self.parse_unary()})"
        if t.text == "-":
            self.next()
            inner = self.parse_unary()
            if re.fullmatch(r"\d+(\.\d+)?", inner):
                return f"(-{inner})"
            return f"(-lw_num({inner}))"
        if t.text == "+":
            self.next()
            inner = self.parse_unary()
            if re.fullmatch(r"\d+(\.\d+)?", inner):
                return inner
            return f"(+lw_num({inner}))"
        if t.text == "~":
            self.next()
            return f"(~{self.parse_unary()})"
        if t.text == "++":
            # prefix increment used as expression is not in our codebase;
            # treat as error to surface it
            raise SyntaxError(f"{self.filename}:{t.line}: prefix ++ unsupported")
        if t.text == "new":
            self.next()
            return self.parse_postfix()
        return self.parse_postfix()

    def parse_postfix(self):
        expr = self.parse_primary()
        while True:
            t = self.peek()
            if t.text == ".":
                self.next()
                name = self.next().text
                if name == "length":  # LS .length? not used, but be safe
                    expr = f"lw_count({expr})"
                else:
                    expr = f"{expr}.{self.ident(name)}"
            elif t.text == "(":
                args = self.parse_args()
                expr = f"{expr}({', '.join(args)})"
            elif t.text == "[":
                self.next()
                idx = self.parse_expression()
                self.expect("]")
                expr = f"lw_get({expr}, {idx})"
            elif t.text in ("++", "--"):
                raise SyntaxError(
                    f"{self.filename}:{t.line}: postfix {t.text} inside expression unsupported")
            else:
                return expr

    def parse_args(self):
        self.expect("(")
        args = []
        while not self.at(")"):
            args.append(self.parse_expression())
            if not self.accept(","):
                break
        self.expect(")")
        return args

    def parse_params(self):
        """Parameter list `(a, b = expr, @c)` -> list of python param strings
        plus the bare names (for locals tracking)."""
        self.expect("(")
        params = []
        names = []
        while not self.at(")"):
            p = self.next().text
            if p == "@":  # reference param marker
                p = self.next().text
            name = self.ident(p)
            if self.accept("="):
                default = self.parse_expression()
                params.append(f"{name}={default}")
            else:
                params.append(name)
            names.append(name)
            if not self.accept(","):
                break
        self.expect(")")
        return params, names

    def parse_primary(self):
        t = self.peek()
        if t.kind == "number":
            self.next()
            return t.text
        if t.kind == "string":
            self.next()
            return t.text
        if t.text == "null":
            self.next()
            return "None"
        if t.text == "true":
            self.next()
            return "True"
        if t.text == "false":
            self.next()
            return "False"
        if t.text == "this":
            self.next()
            return "self"
        if t.text == "super":
            self.next()
            if self.at("("):
                args = self.parse_args()
                return f"super().__init__({', '.join(args)})"
            self.expect(".")
            name = self.next().text
            return f"super().{self.ident(name)}"
        if t.text == "function":
            return self.parse_closure()
        if t.text == "(":
            self.next()
            inner = self.parse_expression()
            self.expect(")")
            return f"({inner})"
        if t.text == "[":
            return self.parse_bracket_literal()
        if t.kind == "ident":
            self.next()
            name = self.ident(t.text)
            # LS resolves statics bare inside the class; Python needs Class.x
            if self.cur_class and name in self.cur_statics and not self.is_local(name):
                return f"{self.cur_class}.{name}"
            # LS implicit this: bare method call inside a class body
            if (self.cur_class and not self.in_static_method
                    and name in self.cur_methods and not self.is_local(name)):
                return f"self.{name}"
            return name
        raise SyntaxError(f"{self.filename}:{t.line}: unexpected {t.text!r} in expression")

    def parse_bracket_literal(self):
        self.expect("[")
        # empty map [:]
        if self.at(":"):
            self.next()
            self.expect("]")
            return "{}"
        if self.at("]"):
            self.next()
            return "[]"
        # parse first element to decide map vs array
        first = self.parse_expression()
        if self.at(":"):
            self.next()
            v = self.parse_expression()
            pairs = [f"{first}: {v}"]
            while self.accept(","):
                if self.at("]"):
                    break
                k = self.parse_expression()
                self.expect(":")
                v = self.parse_expression()
                pairs.append(f"{k}: {v}")
            self.expect("]")
            return "{" + ", ".join(pairs) + "}"
        items = [first]
        while self.accept(","):
            if self.at("]"):
                break
            items.append(self.parse_expression())
        self.expect("]")
        return "[" + ", ".join(items) + "]"

    def parse_closure(self):
        """function(a, b) { ... }  ->  hoisted def, returns its name."""
        fn = self.fn_stack[-1] if self.fn_stack else None
        self.expect("function")
        params, names = self.parse_params()
        if fn is None:
            raise SyntaxError(f"{self.filename}: closure at module level unsupported")
        fn.hoist_counter += 1
        name = f"_lwfn{fn.hoist_counter}_{len(self.fn_stack)}"
        body_lines = self.compile_block_lines(names)
        block = [f"def {name}({', '.join(params)}):"]
        block += ["    " + ln for ln in (body_lines or ["pass"])]
        fn.hoisted.append(block)
        return name

    # ── statements ──

    def compile_block_lines(self, extra_locals=()):
        """Compile a braced { ... } block, return list of Python lines."""
        fn = Fn()
        # inherit surrounding function's locals view? Closures capture outer
        # vars — python closures do too. Track separately for `global` calc.
        fn.locals.update(extra_locals)
        self.fn_stack.append(fn)
        self.expect("{")
        lines = []
        while not self.at("}"):
            lines.extend(self.compile_statement())
        self.expect("}")
        self.fn_stack.pop()
        out = []
        for block in fn.hoisted:
            out.extend(block)
        # global declarations for assigned globals
        gnames = sorted((fn.assigned - fn.locals) & self.global_names)
        if gnames:
            out.insert(0, "global " + ", ".join(gnames))
        out.extend(lines)
        return out

    def note_assign(self, name):
        if self.fn_stack:
            self.fn_stack[-1].assigned.add(name)

    def note_local(self, name):
        if self.fn_stack:
            self.fn_stack[-1].locals.add(name)

    def is_local(self, name):
        return any(name in fn.locals for fn in self.fn_stack)

    def flush_hoisted(self):
        """Emit hoisted closures accumulated for the current statement."""
        fn = self.fn_stack[-1]
        lines = []
        for block in fn.hoisted:
            lines.extend(block)
        fn.hoisted = []
        return lines

    def compile_statement(self):
        """Compile one statement, return list of Python lines."""
        self.skip_semis()
        t = self.peek()
        if t.text == "}":
            return []
        if t.text == "{":
            # bare block
            return self.compile_braced_body()
        if t.text == "if":
            return self.compile_if()
        if t.text == "while":
            return self.compile_while()
        if t.text == "for":
            return self.compile_for()
        if t.text == "return":
            self.next()
            if self.at(";") or self.at("}") or self.peek().line != t.line:
                self.skip_semis()
                return self.flush_hoisted() + ["return None"]
            expr = self.parse_expression()
            self.skip_semis()
            return self.flush_hoisted() + [f"return {expr}"]
        if t.text == "break":
            self.next()
            self.skip_semis()
            return ["break"]
        if t.text == "continue":
            self.next()
            self.skip_semis()
            incr = self.loop_stack[-1] if self.loop_stack else None
            if incr:
                return [incr, "continue"]
            return ["continue"]
        if t.text == "var":
            return self.compile_var_decl()
        if t.text == "global":
            return self.compile_global_decl()
        # expression statement (incl. assignments, ++/--)
        return self.compile_expr_statement()

    def compile_braced_body(self):
        """{ ... } body sharing the CURRENT function context (no new Fn)."""
        self.expect("{")
        lines = []
        while not self.at("}"):
            lines.extend(self.compile_statement())
        self.expect("}")
        return lines

    def compile_body_or_single(self):
        """Either a braced block or a single statement (unbraced if/for)."""
        if self.at("{"):
            body = self.compile_braced_body()
        else:
            body = self.compile_statement()
        return body or ["pass"]

    def compile_if(self):
        self.expect("if")
        self.expect("(")
        cond = self.parse_expression()
        self.expect(")")
        pre = self.flush_hoisted()
        body = self.compile_body_or_single()
        lines = pre + [f"if {cond}:"] + ["    " + ln for ln in body]
        while self.at("else"):
            self.next()
            if self.at("if"):
                # elif chain: compile nested if, splice as elif
                sub = self.compile_if()
                # sub[0] is "if cond:" (possibly preceded by hoisted defs)
                # keep it simple: emit as else: <nested if>
                lines.append("else:")
                lines += ["    " + ln for ln in sub]
                return lines
            ebody = self.compile_body_or_single()
            lines.append("else:")
            lines += ["    " + ln for ln in ebody]
        return lines

    def compile_while(self):
        self.expect("while")
        self.expect("(")
        cond = self.parse_expression()
        self.expect(")")
        pre = self.flush_hoisted()
        self.loop_stack.append(None)
        body = self.compile_body_or_single()
        self.loop_stack.pop()
        return pre + [f"while {cond}:"] + ["    " + ln for ln in body]

    def compile_for(self):
        self.expect("for")
        self.expect("(")
        # foreach: for (var v in coll)
        if self.at("var") and self.peek(2).text == "in":
            self.next()
            v = self.ident(self.next().text)
            self.note_local(v)
            self.expect("in")
            coll = self.parse_expression()
            self.expect(")")
            pre = self.flush_hoisted()
            self.loop_stack.append(None)
            body = self.compile_body_or_single()
            self.loop_stack.pop()
            return pre + [f"for {v} in lw_values({coll}):"] + ["    " + ln for ln in body]
        # C-style: for (init; cond; update)
        init_lines = []
        if not self.at(";"):
            if self.at("var"):
                init_lines = self.compile_var_decl(stop_at_semi=True)
            else:
                init_lines = self.compile_expr_statement(stop_at_semi=True)
        self.expect(";")
        cond = "True"
        if not self.at(";"):
            cond = self.parse_expression()
        self.expect(";")
        update_lines = []
        if not self.at(")"):
            update_lines = self.compile_expr_statement(stop_at_semi=True)
        self.expect(")")
        pre = self.flush_hoisted()
        incr = update_lines[0] if len(update_lines) == 1 else None
        self.loop_stack.append(incr)
        body = self.compile_body_or_single()
        self.loop_stack.pop()
        lines = pre + init_lines
        lines.append(f"while {cond}:")
        lines += ["    " + ln for ln in body]
        lines += ["    " + ln for ln in update_lines]
        return lines

    def compile_var_decl(self, stop_at_semi=False):
        self.expect("var")
        name = self.ident(self.next().text)
        self.note_local(name)
        if self.accept("="):
            expr = self.parse_expression()
        else:
            expr = "None"
        if not stop_at_semi:
            self.skip_semis()
        return self.flush_hoisted() + [f"{name} = {expr}"]

    def compile_global_decl(self):
        """global x / global x = expr — module-level, init once."""
        self.expect("global")
        name = self.ident(self.next().text)
        if self.accept("="):
            expr = self.parse_expression()
        else:
            expr = "None"
        self.skip_semis()
        return [f"{name} = {expr}"]

    ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^="}

    def compile_expr_statement(self, stop_at_semi=False):
        """Assignment / call / increment statement."""
        # Try to detect an assignment: parse LHS as postfix chain first.
        start = self.i
        lhs_info = self.try_parse_lhs()
        if lhs_info is not None:
            kind, target, op = lhs_info
            if op in ("++", "--"):
                pyop = "+" if op == "++" else "-"
                lines = self.emit_augassign(kind, target, pyop, "1")
                if not stop_at_semi:
                    self.skip_semis()
                return lines
            rhs = self.parse_expression()
            if not stop_at_semi:
                self.skip_semis()
            if op == "=":
                lines = self.emit_assign(kind, target, rhs)
            else:
                lines = self.emit_augassign(kind, target, op[0], rhs)
            return self.flush_hoisted() + lines
        # plain expression statement
        self.i = start
        expr = self.parse_expression()
        if not stop_at_semi:
            self.skip_semis()
        return self.flush_hoisted() + [expr]

    def try_parse_lhs(self):
        """Attempt to parse `<postfix-chain> (=|+=|...|++|--)`.

        Returns (kind, target, op) or None (and rewinds) if this is not an
        assignment statement. kind: 'name' | 'attr' | 'sub'.
        target: str for name/attr; (obj, idx) tuple for sub.
        """
        start = self.i
        t = self.peek()
        if t.kind != "ident" and t.text not in ("this",):
            return None
        # parse a restricted postfix chain
        if t.text == "this":
            self.next()
            expr = "self"
        else:
            self.next()
            expr = self.ident(t.text)
        bare_name = expr
        kind = "name"
        sub = None
        while True:
            nt = self.peek()
            if nt.text == ".":
                self.next()
                nm = self.next().text
                expr = f"{expr}.{self.ident(nm)}"
                kind = "attr"
            elif nt.text == "[":
                self.next()
                idx = self.parse_expression()
                self.expect("]")
                sub = (expr, idx)
                expr = f"lw_get({expr}, {idx})"
                kind = "sub"
            elif nt.text == "(":
                # call in the chain -> can still be lhs prefix (rare); parse args
                args = self.parse_args()
                expr = f"{expr}({', '.join(args)})"
                kind = "call"
            else:
                break
        op = self.peek().text
        if op in self.ASSIGN_OPS or op in ("++", "--"):
            if kind == "call":
                # e.g. f()[x] handled above via sub; call as final lhs invalid
                self.i = start
                return None
            self.next()
            if kind == "name":
                self.note_assign(bare_name)
                return ("name", expr, op)
            if kind == "attr":
                return ("attr", expr, op)
            if kind == "sub":
                return ("sub", sub, op)
        self.i = start
        return None

    def emit_assign(self, kind, target, rhs):
        if kind == "sub":
            obj, idx = target
            return [f"lw_put({obj}, {idx}, {rhs})"]
        return [f"{target} = {rhs}"]

    def emit_augassign(self, kind, target, op, rhs):
        if kind == "sub":
            obj, idx = target
            if op == "+":
                return [f"lw_put({obj}, {idx}, lw_add(lw_get({obj}, {idx}), {rhs}))"]
            return [f"lw_put({obj}, {idx}, lw_num(lw_get({obj}, {idx})) {op} lw_num({rhs}))"]
        if op == "+":
            return [f"{target} = lw_add({target}, {rhs})"]
        return [f"{target} = lw_num({target}) {op} lw_num({rhs})"]

    def prescan_class_methods(self):
        """From just after the class '{', collect member method names without
        consuming tokens (LS implicit-this: bare calls resolve to methods)."""
        depth = 1
        j = self.i
        names = set()
        toks = self.toks
        n = len(toks)
        while j < n and depth > 0:
            t = toks[j]
            if t.text == "{":
                depth += 1
            elif t.text == "}":
                depth -= 1
            elif depth == 1 and t.kind == "ident" and j + 1 < n and toks[j + 1].text == "(":
                if t.text not in ("constructor", "static", "private", "public", "protected"):
                    prev = toks[j - 1].text if j > 0 else ""
                    # exclude calls (prev is operator/'(' etc.) — member decls
                    # follow '{', '}', ';' or a modifier keyword
                    if prev in ("{", "}", ";", "static", "private", "public", "protected"):
                        names.add(self.ident(t.text))
            j += 1
        return names

    # ── top-level declarations ──

    def compile_function_decl(self):
        self.expect("function")
        name = self.ident(self.next().text)
        params, names = self.parse_params()
        body = self.compile_block_lines(names)
        lines = [f"def {name}({', '.join(params)}):"]
        lines += ["    " + ln for ln in (body or ["pass"])]
        lines.append("")
        return lines

    def compile_class_decl(self):
        self.expect("class")
        name = self.next().text
        base = None
        if self.accept("extends"):
            base = self.next().text
        self.expect("{")
        statics = []       # (name, expr)
        fields = []        # (name, expr)
        methods = []       # list of line lists
        ctor = None        # (params, body_lines)
        self.class_stack.append(name)
        prev_class, prev_statics = self.cur_class, self.cur_statics
        self.cur_class = name
        # inherited statics resolve bare too
        inherited = set()
        b = base
        while b in self.class_statics:
            bb, bs = self.class_statics[b]
            inherited |= bs
            b = bb
        self.cur_statics = set(inherited)
        prev_methods = self.cur_methods
        inh_methods = set()
        b = base
        while b in self.class_methods:
            bb, bm = self.class_methods[b]
            inh_methods |= bm
            b = bb
        self.cur_methods = inh_methods | self.prescan_class_methods()
        while not self.at("}"):
            self.skip_semis()
            if self.at("}"):
                break
            t = self.peek()
            if t.text in ("private", "public", "protected"):
                self.next()
                t = self.peek()
            if t.text == "static":
                self.next()
                if self.peek(1).text == "(":
                    # static method
                    mname = self.ident(self.next().text)
                    params, names = self.parse_params()
                    self.in_static_method = True
                    body = self.compile_block_lines(names)
                    self.in_static_method = False
                    mlines = ["@staticmethod",
                              f"def {mname}({', '.join(params)}):"]
                    mlines += ["    " + ln for ln in (body or ["pass"])]
                    mlines.append("")
                    methods.append(mlines)
                    continue
                sname = self.ident(self.next().text)
                self.cur_statics.add(sname)
                if self.accept("="):
                    sexpr = self.parse_expression()
                else:
                    sexpr = "None"
                self.skip_semis()
                statics.append((sname, sexpr))
            elif t.text == "constructor":
                self.next()
                params, names = self.parse_params()
                body = self.compile_block_lines(names + ["self"])
                ctor = (params, body)
            elif self.peek(1).text == "(":
                # method
                mname = self.ident(self.next().text)
                params, names = self.parse_params()
                body = self.compile_block_lines(names + ["self"])
                mlines = [f"def {mname}(self{', ' if params else ''}{', '.join(params)}):"]
                mlines += ["    " + ln for ln in (body or ["pass"])]
                mlines.append("")
                methods.append(mlines)
            else:
                # instance field: name = expr  (or bare name)
                fname = self.ident(self.next().text)
                if self.accept("="):
                    fexpr = self.parse_expression()
                else:
                    fexpr = "None"
                self.skip_semis()
                fields.append((fname, fexpr))
        self.expect("}")
        self.class_stack.pop()
        self.class_statics[name] = (base, set(self.cur_statics))
        self.class_methods[name] = (base, set(self.cur_methods))
        self.cur_class, self.cur_statics = prev_class, prev_statics
        self.cur_methods = prev_methods

        head = f"class {name}({base}):" if base else f"class {name}:"
        lines = [head]
        for sname, sexpr in statics:
            lines.append(f"    {sname} = {sexpr}")
        # __init__
        params = ctor[0] if ctor else []
        body = []
        for fname, fexpr in fields:
            body.append(f"self.{fname} = {fexpr}")
        if ctor:
            body += ctor[1]
        elif base:
            body.insert(0, "super().__init__()")
        if not body:
            body = ["pass"]
        lines.append(f"    def __init__(self{', ' if params else ''}{', '.join(params)}):")
        lines += ["        " + ln for ln in body]
        lines.append("")
        for mlines in methods:
            lines += ["    " + ln for ln in mlines]
        lines.append("")
        return lines

    # ── file / module driver ──

    def compile_file(self, path):
        self.filename = str(path)
        source = path.read_text()
        self.load(lex(source, self.filename))
        self.out.append(f"# ════════ {path.name} ════════")
        last_i = -1
        while self.peek().kind != "eof":
            if self.i == last_i:
                t = self.peek()
                raise SyntaxError(
                    f"{self.filename}:{t.line}: parser stuck at {t.text!r}")
            last_i = self.i
            self.skip_semis()
            t = self.peek()
            if t.kind == "eof":
                break
            if t.text == "include":
                # includes are resolved by the assembler (caller), skip here
                self.next()
                self.expect("(")
                inc = self.next().text.strip("'\"")
                self.expect(")")
                self.skip_semis()
                self.includes.append(inc)
                self.out.append(f"# include: {inc} (inlined by assembler)")
                continue
            if t.text == "global":
                self.out.extend(self.compile_global_decl())
                continue
            if t.text == "function":
                self.out.extend(self.compile_function_decl())
                continue
            if t.text == "class":
                self.out.extend(self.compile_class_decl())
                continue
            # top-level executable statement -> goes into turn()
            fn = Fn()
            self.fn_stack.append(fn)
            stmt = self.compile_statement()
            self.fn_stack.pop()
            pre = []
            for block in fn.hoisted:
                pre.extend(block)
            gnames = sorted((fn.assigned - fn.locals) & self.global_names)
            self.toplevel_stmts.append((gnames, pre + stmt))
        self.out.append("")


# ─────────────────────────── Assembly ───────────────────────────

def collect_global_names(files):
    names = set()
    rx = re.compile(r"^\s*global\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
    for f in files:
        for m in rx.finditer(f.read_text()):
            n = m.group(1)
            if n.startswith("__") and not n.endswith("__"):
                n = "lw" + n
            names.add(n)
    return names


def include_order(entry):
    """Resolve include() order depth-first from main.lk (each file once)."""
    seen = []
    rx = re.compile(r"include\(\s*['\"]([^'\"]+)['\"]\s*\)")

    def visit(path):
        if path in seen:
            return
        text = path.read_text()
        pre = []
        for m in rx.finditer(text):
            inc = m.group(1)
            if not inc.endswith(".lk"):
                inc += ".lk"
            cand = SRC_DIR / inc
            if not cand.exists():
                cand = path.parent / inc
            pre.append(cand.resolve())
        # LeekScript include(): file inlined at the include point, so
        # dependencies (includes) are processed before the rest of the file.
        for p in pre:
            visit(p)
        seen.append(path)

    visit(entry)
    return seen


def main():
    check = "--check" in sys.argv
    entry = SRC_DIR / "main.lk"
    files = include_order(entry)
    global_names = collect_global_names(files)

    tr = Transpiler(global_names)
    tr.includes = []
    for f in files:
        tr.compile_file(f)

    prelude = PRELUDE_FILE.read_text()

    turn_globals = set()
    turn_body = []
    for gnames, stmt in tr.toplevel_stmts:
        turn_globals.update(gnames)
        turn_body.extend(stmt)
    turn_lines = ["def turn():"]
    inner = []
    if turn_globals:
        inner.append("global " + ", ".join(sorted(turn_globals)))
    inner.append("try:")
    inner += ["    " + ln for ln in (turn_body or ["pass"])]
    # no stdlib imports here: importing traceback inside the sandbox can
    # itself fail and mask the real error — walk __traceback__ by hand
    inner.append("except Exception as e:")
    inner.append("    tb = e.__traceback__")
    inner.append("    trace = []")
    inner.append("    while tb is not None:")
    inner.append("        trace.append(tb.tb_frame.f_code.co_name + ':' + str(tb.tb_lineno))")
    inner.append("        tb = tb.tb_next")
    inner.append("    debugE('PYERR ' + type(e).__name__ + ': ' + str(e)[:300] + ' @ ' + ' > '.join(trace[-10:]))")
    turn_lines += ["    " + ln for ln in inner]

    out = [prelude, ""] + tr.out + [""] + turn_lines + [""]
    OUT_FILE.parent.mkdir(exist_ok=True)
    OUT_FILE.write_text("\n".join(out))
    print(f"wrote {OUT_FILE} ({len(out)} lines) from {len(files)} modules")

    if check:
        import py_compile
        try:
            py_compile.compile(str(OUT_FILE), doraise=True)
            print("CPython syntax check: OK")
        except py_compile.PyCompileError as e:
            print("SYNTAX ERROR:", e)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
