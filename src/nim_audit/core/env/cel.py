"""CEL (Common Expression Language) to Python translator and evaluator."""

from __future__ import annotations

import re
from typing import Any


class CelError(Exception):
    """Error during CEL evaluation."""

    pass


def cel_matches(val: Any, pattern: str) -> bool:
    """CEL matches() function - check if value matches regex pattern."""
    if val is None:
        return False
    try:
        return re.search(pattern, str(val)) is not None
    except re.error as e:
        raise CelError(f"Invalid regex: {pattern!r}: {e}") from e


def cel_size(x: Any) -> int:
    """CEL size() function - get length of a value."""
    if x is None:
        return 0
    try:
        return len(x)
    except Exception:
        try:
            return sum(1 for _ in x)
        except Exception:
            return 0


def cel_has(x: Any) -> bool:
    """CEL has() function - check if value is present (not None)."""
    return x is not None


def _split_top_level_args(s: str) -> tuple[str, str]:
    """Split 'a, b' at first comma not inside parentheses or quotes."""
    depth = 0
    in_sq = False
    in_dq = False
    for i, ch in enumerate(s):
        if ch == "'" and not in_dq:
            in_sq = not in_sq
        elif ch == '"' and not in_sq:
            in_dq = not in_dq
        elif in_sq or in_dq:
            continue
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            return s[:i].strip(), s[i + 1 :].strip()
    raise CelError("Could not split exists() args")


def _replace_not(expr: str) -> str:
    """Replace CEL '!' with Python 'not', but keep '!='."""
    out = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "!" and (i + 1 >= len(expr) or expr[i + 1] != "="):
            out.append("not ")
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _replace_matches(expr: str) -> str:
    """Replace X.matches('re') with cel_matches(X, 're')."""
    s = expr
    while True:
        m = re.search(r"\.matches\(", s)
        if not m:
            return s
        start = m.start()
        # Find matching close paren for matches(
        i = m.end()
        depth = 1
        in_sq = False
        in_dq = False
        while i < len(s):
            ch = s[i]
            if ch == "'" and not in_dq:
                in_sq = not in_sq
            elif ch == '"' and not in_sq:
                in_dq = not in_dq
            elif in_sq or in_dq:
                pass
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            raise CelError("Unbalanced parentheses in matches()")
        arg = s[m.end() : i].strip()
        # Object expression: from last token boundary to '.matches('
        obj = s[:start].rstrip()
        # Find start of obj by scanning backwards for whitespace / operators
        j = len(obj) - 1
        while j >= 0:
            if obj[j] in " \t\r\n&|=!<>+-*/%,:":
                break
            j -= 1
        obj_expr = obj[j + 1 :].strip()
        prefix = s[: j + 1]
        suffix = s[i + 1 :]
        s = f"{prefix}cel_matches({obj_expr}, {arg}){suffix}"
    return s


def _replace_size(expr: str) -> str:
    """Replace X.size() with cel_size(X)."""
    return re.sub(r"(\b[a-zA-Z_][a-zA-Z0-9_]*\b)\.size\(\)", r"cel_size(\1)", expr)


def _replace_exists(expr: str) -> str:
    """Handle pattern: <map>.keys().exists(var, predicate)."""
    s = expr
    while True:
        m = re.search(r"(\b[a-zA-Z_][a-zA-Z0-9_]*\b)\.keys\(\)\.exists\(", s)
        if not m:
            return s
        map_name = m.group(1)
        # Find closing paren of exists(
        i = m.end()
        depth = 1
        in_sq = False
        in_dq = False
        while i < len(s):
            ch = s[i]
            if ch == "'" and not in_dq:
                in_sq = not in_sq
            elif ch == '"' and not in_sq:
                in_dq = not in_dq
            elif in_sq or in_dq:
                pass
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        if depth != 0:
            raise CelError("Unbalanced parentheses in exists()")
        inside = s[m.end() : i].strip()
        var, pred = _split_top_level_args(inside)
        pred_py = cel_to_py(pred)  # recurse
        replacement = f"any(({pred_py}) for {var} in {map_name}.keys())"
        s = s[: m.start()] + replacement + s[i + 1 :]
    return s


def cel_to_py(expr: str) -> str:
    """
    Convert a CEL expression to Python.

    Handles:
    - && -> and, || -> or
    - true/false -> True/False
    - X.matches('re') -> cel_matches(X, 're')
    - X.size() -> cel_size(X)
    - has(X) -> cel_has(X)
    - map.keys().exists(v, pred) -> any((pred_py) for v in map.keys())
    - ! -> not (but not !=)
    """
    if not isinstance(expr, str):
        raise CelError("CEL expression must be a string")
    s = expr.strip()

    # Operators and literals
    s = s.replace("&&", " and ").replace("||", " or ")
    s = re.sub(r"\btrue\b", "True", s, flags=re.IGNORECASE)
    s = re.sub(r"\bfalse\b", "False", s, flags=re.IGNORECASE)

    # Functions/methods
    s = _replace_matches(s)
    s = _replace_exists(s)
    s = _replace_size(s)
    s = re.sub(r"\bhas\(", "cel_has(", s)

    # Not operator last (avoid touching !=)
    s = _replace_not(s)
    return s


def eval_cel(expr: str, context: dict[str, Any]) -> bool:
    """
    Evaluate a CEL expression with the given context.

    Args:
        expr: CEL expression string
        context: Variables available during evaluation (e.g., {"env": {...}, "meta": {...}})

    Returns:
        Boolean result of the expression

    Raises:
        CelError: If evaluation fails
    """
    py = cel_to_py(expr)
    safe_globals = {
        "__builtins__": {},
        "cel_matches": cel_matches,
        "cel_size": cel_size,
        "cel_has": cel_has,
        "any": any,
        "all": all,
        "int": int,
    }
    try:
        return bool(eval(py, safe_globals, dict(context)))
    except Exception as e:
        raise CelError(f"CEL eval failed. expr={expr!r} py={py!r} err={e}") from e
