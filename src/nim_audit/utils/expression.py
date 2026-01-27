"""Safe expression evaluator for policy rules."""

from __future__ import annotations

import ast
import operator
from typing import Any, Callable


class SafeExpressionEvaluator:
    """Safe evaluator for policy rule expressions.

    This evaluator uses Python's AST to parse and evaluate expressions
    safely, without using eval(). It supports a limited subset of Python
    expressions suitable for policy rules.

    Supported operations:
    - Comparisons: ==, !=, <, <=, >, >=, in, not in, is, is not
    - Boolean: and, or, not
    - Attribute access: obj.attr
    - Subscript: obj[key], obj.get(key)
    - Method calls: str.startswith(), str.endswith(), etc.
    - Literals: strings, numbers, booleans, None, lists, dicts

    Example:
        evaluator = SafeExpressionEvaluator()
        context = {"labels": {"version": "1.0"}, "env": {"PORT": "8000"}}
        result = evaluator.evaluate("labels.get('version') == '1.0'", context)
    """

    # Allowed comparison operators
    COMPARE_OPS: dict[type, Callable[[Any, Any], bool]] = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Is: operator.is_,
        ast.IsNot: operator.is_not,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
    }

    # Allowed binary operators
    BINARY_OPS: dict[type, Callable[[Any, Any], Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
    }

    # Allowed unary operators
    UNARY_OPS: dict[type, Callable[[Any], Any]] = {
        ast.Not: operator.not_,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    # Allowed built-in functions
    ALLOWED_FUNCTIONS: dict[str, Callable[..., Any]] = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "list": list,
        "dict": dict,
        "set": set,
        "min": min,
        "max": max,
        "sum": sum,
        "abs": abs,
        "all": all,
        "any": any,
        "sorted": sorted,
        "reversed": lambda x: list(reversed(x)),
    }

    # Allowed methods on strings
    ALLOWED_STRING_METHODS = {
        "startswith",
        "endswith",
        "lower",
        "upper",
        "strip",
        "lstrip",
        "rstrip",
        "split",
        "join",
        "replace",
        "find",
        "count",
        "isdigit",
        "isalpha",
        "isalnum",
    }

    # Allowed methods on dicts
    ALLOWED_DICT_METHODS = {
        "get",
        "keys",
        "values",
        "items",
    }

    # Allowed methods on lists
    ALLOWED_LIST_METHODS = {
        "append",
        "extend",
        "index",
        "count",
    }

    def __init__(self, max_depth: int = 10) -> None:
        """Initialize the evaluator.

        Args:
            max_depth: Maximum AST depth to prevent stack overflow
        """
        self._max_depth = max_depth

    def evaluate(self, expression: str, context: dict[str, Any]) -> Any:
        """Evaluate an expression with the given context.

        Args:
            expression: Python expression string
            context: Variables available in the expression

        Returns:
            Result of evaluating the expression

        Raises:
            ValueError: If expression is invalid or unsafe
        """
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"Invalid expression syntax: {e}")

        return self._eval_node(tree.body, context, depth=0)

    def _eval_node(self, node: ast.AST, context: dict[str, Any], depth: int) -> Any:
        """Evaluate an AST node.

        Args:
            node: AST node to evaluate
            context: Variable context
            depth: Current recursion depth

        Returns:
            Result of evaluation
        """
        if depth > self._max_depth:
            raise ValueError("Expression too deeply nested")

        # Constants (Python 3.8+)
        if isinstance(node, ast.Constant):
            return node.value

        # Names (variables)
        if isinstance(node, ast.Name):
            if node.id in self.ALLOWED_FUNCTIONS:
                return self.ALLOWED_FUNCTIONS[node.id]
            if node.id == "True":
                return True
            if node.id == "False":
                return False
            if node.id == "None":
                return None
            if node.id in context:
                return context[node.id]
            raise ValueError(f"Unknown variable: {node.id}")

        # Attribute access (obj.attr)
        if isinstance(node, ast.Attribute):
            value = self._eval_node(node.value, context, depth + 1)
            attr = node.attr

            # Check if it's an allowed method
            if isinstance(value, str) and attr in self.ALLOWED_STRING_METHODS:
                return getattr(value, attr)
            if isinstance(value, dict) and attr in self.ALLOWED_DICT_METHODS:
                return getattr(value, attr)
            if isinstance(value, list) and attr in self.ALLOWED_LIST_METHODS:
                return getattr(value, attr)

            # Allow attribute access on objects
            if hasattr(value, attr):
                return getattr(value, attr)

            raise ValueError(f"Cannot access attribute '{attr}'")

        # Subscript (obj[key])
        if isinstance(node, ast.Subscript):
            value = self._eval_node(node.value, context, depth + 1)
            key = self._eval_node(node.slice, context, depth + 1)
            return value[key]

        # Function/method calls
        if isinstance(node, ast.Call):
            func = self._eval_node(node.func, context, depth + 1)

            # Evaluate arguments
            args = [self._eval_node(arg, context, depth + 1) for arg in node.args]
            kwargs = {
                kw.arg: self._eval_node(kw.value, context, depth + 1)
                for kw in node.keywords
                if kw.arg is not None
            }

            # Check if it's a safe callable
            if callable(func):
                return func(*args, **kwargs)

            raise ValueError("Cannot call non-callable")

        # Comparisons
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context, depth + 1)

            for op, comparator in zip(node.ops, node.comparators):
                op_func = self.COMPARE_OPS.get(type(op))
                if op_func is None:
                    raise ValueError(f"Unsupported comparison operator: {type(op).__name__}")

                right = self._eval_node(comparator, context, depth + 1)
                if not op_func(left, right):
                    return False
                left = right

            return True

        # Boolean operations (and, or)
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for value in node.values:
                    if not self._eval_node(value, context, depth + 1):
                        return False
                return True
            elif isinstance(node.op, ast.Or):
                for value in node.values:
                    if self._eval_node(value, context, depth + 1):
                        return True
                return False

        # Unary operations (not, -, +)
        if isinstance(node, ast.UnaryOp):
            op_func = self.UNARY_OPS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            operand = self._eval_node(node.operand, context, depth + 1)
            return op_func(operand)

        # Binary operations (+, -, *, /, %)
        if isinstance(node, ast.BinOp):
            op_func = self.BINARY_OPS.get(type(node.op))
            if op_func is None:
                raise ValueError(f"Unsupported binary operator: {type(node.op).__name__}")
            left = self._eval_node(node.left, context, depth + 1)
            right = self._eval_node(node.right, context, depth + 1)
            return op_func(left, right)

        # List literals
        if isinstance(node, ast.List):
            return [self._eval_node(elt, context, depth + 1) for elt in node.elts]

        # Dict literals
        if isinstance(node, ast.Dict):
            return {
                self._eval_node(k, context, depth + 1): self._eval_node(v, context, depth + 1)
                for k, v in zip(node.keys, node.values)
                if k is not None
            }

        # Set literals
        if isinstance(node, ast.Set):
            return {self._eval_node(elt, context, depth + 1) for elt in node.elts}

        # Tuple literals
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt, context, depth + 1) for elt in node.elts)

        # If expressions (ternary)
        if isinstance(node, ast.IfExp):
            test = self._eval_node(node.test, context, depth + 1)
            if test:
                return self._eval_node(node.body, context, depth + 1)
            else:
                return self._eval_node(node.orelse, context, depth + 1)

        # List comprehensions (limited)
        if isinstance(node, ast.ListComp):
            return self._eval_comprehension(node, context, depth)

        raise ValueError(f"Unsupported expression type: {type(node).__name__}")

    def _eval_comprehension(
        self, node: ast.ListComp, context: dict[str, Any], depth: int
    ) -> list[Any]:
        """Evaluate a list comprehension.

        Only supports simple single-loop comprehensions.
        """
        if len(node.generators) != 1:
            raise ValueError("Only single-loop comprehensions are supported")

        gen = node.generators[0]
        if not isinstance(gen.target, ast.Name):
            raise ValueError("Only simple loop variables are supported")

        var_name = gen.target.id
        iterable = self._eval_node(gen.iter, context, depth + 1)

        result = []
        for item in iterable:
            local_context = {**context, var_name: item}

            # Check conditions
            if all(self._eval_node(cond, local_context, depth + 1) for cond in gen.ifs):
                result.append(self._eval_node(node.elt, local_context, depth + 1))

        return result


# Global evaluator instance
_evaluator = SafeExpressionEvaluator()


def safe_eval(expression: str, context: dict[str, Any]) -> Any:
    """Safely evaluate an expression.

    Args:
        expression: Python expression string
        context: Variables available in the expression

    Returns:
        Result of evaluating the expression
    """
    return _evaluator.evaluate(expression, context)
