"""Lightweight rule engine for evaluating condition_expression from approval_rules.

Supported syntax (case-insensitive):
  - ``field >= 50000``
  - ``field = 'BR'``
  - ``field IN ('a', 'b', 'c')``
  - ``field IS NULL`` / ``field IS NOT NULL``
  - ``AND`` / ``OR`` combinators (no parentheses – left-to-right evaluation)

The evaluator operates on a flat dict (serialized DecisionContext) and returns
True/False.  Unknown fields evaluate to None; comparisons with None always
return False (SQL-like NULL semantics).

This is intentionally *not* a full SQL parser – it handles the simple
condition_expression strings stored in approval_rules and nothing else.
"""

from __future__ import annotations

import re
from typing import Any

# Pre-compiled patterns
_CMP_RE = re.compile(
    r"(\w+)\s*(>=|<=|!=|<>|>|<|=)\s*('(?:[^']*)'|[\d.]+)",
    re.IGNORECASE,
)
_IN_RE = re.compile(
    r"(\w+)\s+IN\s*\(\s*((?:'[^']*'(?:\s*,\s*'[^']*')*)|(?:[\d.]+(?:\s*,\s*[\d.]+)*))\s*\)",
    re.IGNORECASE,
)
_IS_NULL_RE = re.compile(r"(\w+)\s+IS\s+NULL", re.IGNORECASE)
_IS_NOT_NULL_RE = re.compile(r"(\w+)\s+IS\s+NOT\s+NULL", re.IGNORECASE)


def _coerce(raw: str) -> str | float:
    """Coerce a literal token to float or stripped string."""
    raw = raw.strip()
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    try:
        return float(raw)
    except ValueError:
        return raw


def _field_value(ctx: dict[str, Any], field: str) -> Any:
    """Lookup a field in the context dict (case-insensitive)."""
    # Direct lookup
    v = ctx.get(field)
    if v is not None:
        return v
    # Case-insensitive fallback
    lower = field.lower()
    for k, val in ctx.items():
        if k.lower() == lower:
            return val
    return None


def _eval_single(ctx: dict[str, Any], expr: str) -> bool:
    """Evaluate a single atomic condition (no AND/OR)."""
    expr = expr.strip()
    if not expr:
        return True  # empty expression = always match

    # IS NOT NULL
    m = _IS_NOT_NULL_RE.fullmatch(expr)
    if m:
        return _field_value(ctx, m.group(1)) is not None

    # IS NULL
    m = _IS_NULL_RE.fullmatch(expr)
    if m:
        return _field_value(ctx, m.group(1)) is None

    # IN (...)
    m = _IN_RE.fullmatch(expr)
    if m:
        field_val = _field_value(ctx, m.group(1))
        if field_val is None:
            return False
        items_raw = m.group(2)
        items = [_coerce(s.strip()) for s in re.split(r",", items_raw) if s.strip()]
        # Compare as strings (case-insensitive) or numbers
        for item in items:
            if isinstance(item, float) and isinstance(field_val, (int, float)):
                if float(field_val) == item:
                    return True
            elif str(field_val).lower() == str(item).lower():
                return True
        return False

    # Comparison operators: field >= 123  /  field = 'BR'
    m = _CMP_RE.fullmatch(expr)
    if m:
        field_val = _field_value(ctx, m.group(1))
        if field_val is None:
            return False
        op = m.group(2)
        rhs = _coerce(m.group(3))
        # Numeric comparison
        if isinstance(rhs, float):
            try:
                lhs = float(field_val)
            except (ValueError, TypeError):
                return False
            if op == ">=":
                return lhs >= rhs
            if op == "<=":
                return lhs <= rhs
            if op == ">":
                return lhs > rhs
            if op == "<":
                return lhs < rhs
            if op in ("=", "=="):
                return lhs == rhs
            if op in ("!=", "<>"):
                return lhs != rhs
        else:
            # String comparison (case-insensitive)
            lhs_s = str(field_val).lower()
            rhs_s = str(rhs).lower()
            if op in ("=", "=="):
                return lhs_s == rhs_s
            if op in ("!=", "<>"):
                return lhs_s != rhs_s
            # lexicographic for >=, <=, >, <
            if op == ">=":
                return lhs_s >= rhs_s
            if op == "<=":
                return lhs_s <= rhs_s
            if op == ">":
                return lhs_s > rhs_s
            if op == "<":
                return lhs_s < rhs_s

    # If we can't parse, log and return False (safe default)
    return False


def evaluate_condition(ctx: dict[str, Any], expression: str | None) -> bool:
    """Evaluate a condition_expression against a context dict.

    Returns True if the expression matches.  A None/empty expression always
    matches (rule applies unconditionally).
    """
    if not expression or not expression.strip():
        return True

    # Split by AND / OR (simple left-to-right, no precedence)
    # We split on ' AND ' and ' OR ' tokens (case-insensitive)
    parts = re.split(r"\s+(AND|OR)\s+", expression.strip(), flags=re.IGNORECASE)

    if len(parts) == 1:
        return _eval_single(ctx, parts[0])

    # parts = [cond1, 'AND', cond2, 'OR', cond3, ...]
    result = _eval_single(ctx, parts[0])
    i = 1
    while i < len(parts) - 1:
        combinator = parts[i].upper()
        next_val = _eval_single(ctx, parts[i + 1])
        if combinator == "AND":
            result = result and next_val
        else:  # OR
            result = result or next_val
        i += 2

    return result
