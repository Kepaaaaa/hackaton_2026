"""Tests for intent_engine. Owner: T3."""

from __future__ import annotations

import inspect

import pytest
from conftest import NOW, make_customer, make_moment, make_signal
from pydantic import ValidationError

from app.engines import intent_engine
from app.engines.intent_engine import IntentEngine, path_exists
from app.models.common import IntentType, MomentType, SignalType
from app.rules.intents import INTENT_MIN_CONFIDENCE, INTENT_RULES
from app.rules.schema import IntentRule, ProfileAdjustment

I, M, S = IntentType, MomentType, SignalType

BEGINNER = make_customer(
    profile={
        "life_stage": "young_professional",
        "employment": {"status": "employed", "type": "salaried"},
        "income_stage": "first_recurring_salary",
        "housing": {"status": "tenant", "mortgage": False},
        "family": {"status": "single", "children": 0},
        "financial_profile": {"savings_level": "low", "income_stability": "stable", "financial_maturity": "beginner"},
    }
)


def compute(moments, signals=(), customer=None, rules=None):
    return IntentEngine(rules).compute(customer or make_customer(), moments, list(signals), NOW)


def by_type(intents):
    return {i.type: i for i in intents}


def test_first_salary_lucas_like():
    intents = by_type(
        compute([make_moment(M.FIRST_SALARY, 0.95)], [make_signal(S.LOW_EMERGENCY_BUFFER, source="pattern")], customer=BEGINNER)
    )
    assert intents[I.BUILD_FINANCIAL_SAFETY].confidence >= 0.85
    assert intents[I.START_SAVING].confidence >= 0.70
    assert intents[I.START_INVESTING].confidence <= 0.40
    assert intents[I.START_INVESTING].confidence == pytest.approx(0.2 * 0.95 - 0.05)
    # Several intents at once, sorted by confidence.
    assert len(intents) >= 4
    confidences = [i.confidence for i in compute([make_moment(M.FIRST_SALARY, 0.95)], customer=BEGINNER)]
    assert confidences == sorted(confidences, reverse=True)


def test_multiple_intents_from_new_parent():
    intents = by_type(compute([make_moment(M.NEW_PARENT, 0.9)]))
    assert {I.CHILD_SAVING, I.HOUSEHOLD_BUDGET_ADAPTATION, I.FAMILY_PROTECTION} <= set(intents)
    assert intents[I.CHILD_SAVING].related_moments == [M.NEW_PARENT]


def test_evidence_adds_up_and_is_labelled():
    intents = compute([make_moment(M.FIRST_SALARY, 0.95)], [make_signal(S.LOW_EMERGENCY_BUFFER, source_event_ids=["e7"])],
                      customer=BEGINNER)
    for intent in intents:
        assert sum(e.contribution for e in intent.evidence) == pytest.approx(intent.confidence, abs=1e-6)
    safety = by_type(intents)[I.BUILD_FINANCIAL_SAFETY]
    assert {e.kind for e in safety.evidence} == {"moment", "signal"}
    assert next(e for e in safety.evidence if e.kind == "signal").source_event_ids == ["e7"]
    budgeting = by_type(intents)[I.LEARN_BUDGETING]
    assert any(e.kind == "profile" for e in budgeting.evidence)


def test_confidence_capped_at_one():
    intents = by_type(compute([make_moment(M.FIRST_SALARY, 1.0), make_moment(M.CASHFLOW_PRESSURE, 1.0)],
                              [make_signal(S.LOW_EMERGENCY_BUFFER)]))
    safety = intents[I.BUILD_FINANCIAL_SAFETY]
    assert safety.confidence == 1.0
    assert safety.evidence[-1].kind == "rule"


def test_emerging_moments_produce_no_intents():
    assert compute([make_moment(M.CAR_PROJECT, 0.25)]) == []


def test_profile_alone_never_creates_an_intent():
    assert compute([], customer=BEGINNER) == []


def test_below_min_confidence_dropped():
    rule = IntentRule(intent=I.PROTECT_CAR, moment_weights={M.CAR_PROJECT: 0.1})
    assert compute([make_moment(M.CAR_PROJECT, 0.5)], rules=[rule]) == []
    assert INTENT_MIN_CONFIDENCE == 0.10


def test_expired_signals_ignored():
    rule = IntentRule(intent=I.CHILD_SAVING, signal_weights={S.CHILD_SAVINGS_PAGE_VIEW: 0.5})
    assert compute([], [make_signal(S.CHILD_SAVINGS_PAGE_VIEW, days_ago=10, ttl_days=5)], rules=[rule]) == []
    assert len(compute([], [make_signal(S.CHILD_SAVINGS_PAGE_VIEW, days_ago=1)], rules=[rule])) == 1


def test_no_moments_no_intents():
    assert compute([]) == []


# --- age is never a rule input -------------------------------------------------------------------


@pytest.mark.parametrize("path", ["age", "age_band", "age.years"])
def test_age_adjustment_rejected_by_schema(path):
    with pytest.raises(ValidationError):
        ProfileAdjustment(path=path, equals=30, delta=0.1)


def test_no_rule_references_age():
    for rule in INTENT_RULES:
        for adj in rule.profile_adjustments:
            assert not adj.path.split(".")[0].startswith("age")


def test_every_profile_path_exists():
    for rule in INTENT_RULES:
        for adj in rule.profile_adjustments:
            assert path_exists(adj.path), adj.path
    assert not path_exists("financial_profile.nope")


def test_every_intent_has_a_rule():
    assert {r.intent for r in INTENT_RULES} == set(IntentType)


def test_engine_contains_no_intent_or_moment_names():
    src = inspect.getsource(intent_engine)
    for name in [*IntentType, *MomentType, *SignalType]:
        assert name.value not in src
