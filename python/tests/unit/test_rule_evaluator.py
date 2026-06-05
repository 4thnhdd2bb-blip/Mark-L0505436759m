"""
METACOD GLP-1 module — unit tests for the rule DSL evaluator.

Two priorities:
  - Safety: the DSL must reject anything that resembles code execution.
    No eval, no exec, no attribute traversal that escapes the context.
  - Correctness: every supported operator and combinator returns the right
    boolean for representative inputs.
"""

from __future__ import annotations

import pytest


# ============================================================================
# Safety
# ============================================================================

@pytest.mark.unit
def test_evaluator_does_not_use_eval_or_exec():
    """Static guarantee: the evaluator file must not contain eval/exec calls."""
    import inspect
    from pharmacist_agent import RuleEvaluator

    src = inspect.getsource(RuleEvaluator)
    assert "eval(" not in src, "Rule evaluator must not use eval()"
    assert "exec(" not in src, "Rule evaluator must not use exec()"
    assert "__import__" not in src, "Rule evaluator must not call __import__"
    assert "compile(" not in src, "Rule evaluator must not call compile()"


@pytest.mark.unit
def test_evaluator_ignores_unknown_operators_safely():
    """Unknown operators return False rather than raising or executing anything."""
    from pharmacist_agent import RuleEvaluator

    condition = {"field": "x", "shell_exec": "rm -rf /"}
    assert RuleEvaluator.evaluate(condition, {"x": "anything"}) is False


@pytest.mark.unit
def test_evaluator_handles_missing_field_safely():
    """Missing dotted paths resolve to None and yield False for comparisons."""
    from pharmacist_agent import RuleEvaluator

    ctx = {"patient": {}, "drug": {}}

    assert RuleEvaluator.evaluate({"field": "patient.no_such_field", "eq": True}, ctx) is False
    assert RuleEvaluator.evaluate({"field": "patient.no_such_field", "lt": 50}, ctx) is False
    assert RuleEvaluator.evaluate({"field": "drug.deeply.nested.missing", "gt": 0}, ctx) is False


@pytest.mark.unit
def test_evaluator_type_mismatch_returns_false_not_raise():
    """Comparing a string with a number must not raise."""
    from pharmacist_agent import RuleEvaluator

    ctx = {"patient": {"age": "not-a-number"}}
    assert RuleEvaluator.evaluate({"field": "patient.age", "lt": 18}, ctx) is False


# ============================================================================
# Correctness — leaf operators
# ============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("operator,value,target,expected", [
    ("eq", "a", "a", True),
    ("eq", "a", "b", False),
    ("neq", "a", "b", True),
    ("neq", "a", "a", False),
    ("lt", 5, 10, True),
    ("lt", 10, 5, False),
    ("lte", 10, 10, True),
    ("lt", 10, 10, False),
    ("gt", 10, 5, True),
    ("gte", 10, 10, True),
])
def test_leaf_operators(operator, value, target, expected):
    from pharmacist_agent import RuleEvaluator

    ctx = {"x": value}
    condition = {"field": "x", operator: target}
    assert RuleEvaluator.evaluate(condition, ctx) is expected


@pytest.mark.unit
def test_in_operator():
    from pharmacist_agent import RuleEvaluator

    ctx = {"patient": {"child_pugh": "B"}}
    assert RuleEvaluator.evaluate(
        {"field": "patient.child_pugh", "in": ["B", "C"]}, ctx
    ) is True
    assert RuleEvaluator.evaluate(
        {"field": "patient.child_pugh", "in": ["A"]}, ctx
    ) is False


# ============================================================================
# Correctness — logical combinators
# ============================================================================

@pytest.mark.unit
def test_and_combinator():
    from pharmacist_agent import RuleEvaluator

    ctx = {"a": 1, "b": 2}

    assert RuleEvaluator.evaluate({"and": [
        {"field": "a", "eq": 1},
        {"field": "b", "eq": 2},
    ]}, ctx) is True

    assert RuleEvaluator.evaluate({"and": [
        {"field": "a", "eq": 1},
        {"field": "b", "eq": 99},
    ]}, ctx) is False


@pytest.mark.unit
def test_or_combinator():
    from pharmacist_agent import RuleEvaluator

    ctx = {"a": 1, "b": 2}

    assert RuleEvaluator.evaluate({"or": [
        {"field": "a", "eq": 99},
        {"field": "b", "eq": 2},
    ]}, ctx) is True

    assert RuleEvaluator.evaluate({"or": [
        {"field": "a", "eq": 99},
        {"field": "b", "eq": 99},
    ]}, ctx) is False


@pytest.mark.unit
def test_not_combinator():
    from pharmacist_agent import RuleEvaluator

    ctx = {"a": 1}

    assert RuleEvaluator.evaluate({"not": {"field": "a", "eq": 99}}, ctx) is True
    assert RuleEvaluator.evaluate({"not": {"field": "a", "eq": 1}}, ctx) is False


@pytest.mark.unit
def test_nested_combinators():
    """Realistic rule: drug is DOAC AND (eGFR<50 OR (bariatric AND <6 months))."""
    from pharmacist_agent import RuleEvaluator

    ctx = {
        "drug": {"class": "DOAC"},
        "patient": {
            "labs": {"egfr_ml_min": 70},
            "bariatric_type": "RYGB",
            "months_since_bariatric": 3,
        },
    }

    rule = {"and": [
        {"field": "drug.class", "eq": "DOAC"},
        {"or": [
            {"field": "patient.labs.egfr_ml_min", "lt": 50},
            {"and": [
                {"field": "patient.bariatric_type", "neq": "none"},
                {"field": "patient.months_since_bariatric", "lt": 6},
            ]},
        ]},
    ]}

    assert RuleEvaluator.evaluate(rule, ctx) is True


# ============================================================================
# Field path traversal
# ============================================================================

@pytest.mark.unit
def test_dotted_path_walks_dicts_and_objects():
    """Path resolver handles both dict access and attribute access."""
    from pharmacist_agent import RuleEvaluator

    class _Obj:
        def __init__(self):
            self.nested = {"value": 42}

    ctx = {"thing": _Obj()}
    assert RuleEvaluator._get_field(ctx, "thing.nested.value") == 42
