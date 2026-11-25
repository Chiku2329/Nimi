"""Safe arithmetic evaluation and deterministic natural-language arithmetic detection."""
from __future__ import annotations

import ast
import math
import operator
import re


OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}
FUNCS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "abs": abs, "round": round,
}
CONSTS = {"pi": math.pi, "e": math.e}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("exponent too large")
        return OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _eval(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.Name) and node.id in CONSTS:
        return CONSTS[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCS:
        return FUNCS[node.func.id](*[_eval(arg) for arg in node.args])
    raise ValueError("unsupported expression")


def calculate_expression(expression: str) -> str:
    if not isinstance(expression, str) or len(expression) > 256:
        raise ValueError("expression too long")
    tree = ast.parse(expression.replace("^", "**"), mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 80:
        raise ValueError("expression too complex")
    result = _eval(tree.body)
    if isinstance(result, (int, float)) and (not math.isfinite(result) or abs(result) > 1e100):
        raise ValueError("result out of range")
    return str(result)


_NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
_WORD_OPERATIONS = [
    (r"multiply\s+(" + _NUMBER + r")\s+by\s+(" + _NUMBER + r")", "*"),
    (r"(" + _NUMBER + r")\s+multiplied\s+by\s+(" + _NUMBER + r")", "*"),
    (r"(" + _NUMBER + r")\s+times\s+(" + _NUMBER + r")", "*"),
    (r"(" + _NUMBER + r")\s+divided\s+by\s+(" + _NUMBER + r")", "/"),
    (r"(" + _NUMBER + r")\s+plus\s+(" + _NUMBER + r")", "+"),
    (r"(" + _NUMBER + r")\s+minus\s+(" + _NUMBER + r")", "-"),
]


def extract_arithmetic_expression(text: str) -> str | None:
    """Recognize short, unambiguous two-number arithmetic requests."""
    if not isinstance(text, str) or len(text) > 256:
        return None
    cleaned = text.strip().lower()
    cleaned = re.sub(r"^(?:what is|what's|calculate|compute|solve)\s+", "", cleaned)
    cleaned = cleaned.rstrip(" ?.!")

    # Direct arithmetic such as "25 * 4" or "25 × 4".
    direct = re.fullmatch(
        r"(" + _NUMBER + r")\s*([+*/%]|-|×|÷|x)\s*(" + _NUMBER + r")",
        cleaned,
    )
    if direct:
        left, symbol, right = direct.groups()
        symbol = {"×": "*", "x": "*", "÷": "/"}.get(symbol, symbol)
        return f"{left} {symbol} {right}"

    for pattern, operator_symbol in _WORD_OPERATIONS:
        match = re.fullmatch(pattern, cleaned)
        if match:
            left, right = match.groups()
            return f"{left} {operator_symbol} {right}"
    return None
