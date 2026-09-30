"""Tests for decision_engine and the journey catalog. Owner: T4."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import NOW, make_customer, make_event, make_intent, make_moment, make_snapshot

from app.engines.decision_engine import DecisionEngine
from app.models.common import DecisionLevel, DecisionType, IntentType, JourneyType
from app.rules.decisions import DECISION_RULES
from app.rules.journeys import JOURNEYS
from app.rules.schema import SuppressionRule

# Snapshot of a first-salary customer: low buffer, positive projection.
FIRST_SALARY_SNAPSHOT = dict(
    current_balance=3_280, savings_balance=1_800, liquid_balance=5_080, monthly_income=2_450,
    avg_monthly_spending=1_600, projected_balance_before_next_income=1_787, emergency_buffer_months=2.2,
    monthly_margin=850,
)
# Same customer after a large unexpected expense.
SHOCK_SNAPSHOT = dict(FIRST_SALARY_SNAPSHOT, current_balance=1_780, projected_balance_before_next_income=287,
                      emergency_buffer_months=1.24)


def _products(*names):
    return [{"product": n, "since": "2020-01-01"} for n in ("current_account", "savings_account", *names)]


def _first_salary_inputs():
    moments = [make_moment("FIRST_SALARY", 0.95, days_ago=2, ttl_days=90)]
    intents = [
        make_intent("BUILD_FINANCIAL_SAFETY", 0.96, ["FIRST_SALARY"]),
        make_intent("START_SAVING", 0.81, ["FIRST_SALARY"]),
        make_intent("START_INVESTING", 0.14, ["FIRST_SALARY"]),
    ]
    return moments, intents


def _decide(customer=None, snapshot=None, moments=(), intents=(), events=(), engine=None):
    return (engine or DecisionEngine()).decide(
        customer or make_customer(), snapshot or make_snapshot(), list(moments), list(intents), list(events), NOW
    )


# --- Journey catalog ------------------------------------------------------------------------


def test_every_intent_is_served_by_a_journey():
    served = {i for j in JOURNEYS.values() for i in j.serves_intents}
    assert served == set(IntentType)
    assert set(JOURNEYS) == set(JourneyType)


def test_calculator_names_exist():
    from app.engines.calculators import CALCULATORS

    assert all(a.calculator in CALCULATORS for j in JOURNEYS.values() for a in j.actions if a.calculator)


# --- Decisions ------------------------------------------------------------------------------


def test_first_salary_gives_financial_foundation_proactive():
    moments, intents = _first_salary_inputs()
    d = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents)
    assert d.primary.journey == JourneyType.FINANCIAL_FOUNDATION
    assert d.level == DecisionLevel.PROACTIVE
    assert d.decision_type == DecisionType.SHOW_JOURNEY
    low = next(s for s in d.suppressed if s.journey == JourneyType.INVESTMENT_START)
    assert low.rule == "LOW_CONFIDENCE"
    assert d.reasons and all(isinstance(r, str) for r in d.reasons)


def test_score_breakdown_sums_to_total():
    moments, intents = _first_salary_inputs()
    d = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents)
    for c in d.considered:
        b = c.breakdown
        parts = sum(b.weights[k] * getattr(b, k) for k in b.weights) - b.penalties
        assert b.total == pytest.approx(parts, abs=1e-3)
        assert sum(e.contribution for e in c.evidence) == pytest.approx(b.total, abs=1e-3)


def test_travel_covered_shows_service_never_product():
    customer = make_customer(products=_products("travel_insurance"))
    d = _decide(
        customer=customer,
        moments=[make_moment("TRAVEL", 0.73, ttl_days=30)],
        intents=[make_intent("PREPARE_TRIP", 0.66, ["TRAVEL"])],
    )
    assert d.primary.journey == JourneyType.TRAVEL_READY
    assert d.decision_type == DecisionType.SHOW_SERVICE
    assert all(c.decision_type != DecisionType.SHOW_PRODUCT for c in d.considered)
    assert any(e.kind == "product" and e.ref == "travel_insurance" for e in d.primary.evidence)


def test_cashflow_risk_suppresses_investing_and_support_is_primary():
    moments = [
        make_moment("INVESTMENT_INTEREST", 0.9, days_ago=1, ttl_days=45),
        make_moment("CASHFLOW_PRESSURE", 0.95, ttl_days=14),
    ]
    intents = [
        make_intent("START_INVESTING", 0.9, ["INVESTMENT_INTEREST"]),
        make_intent("STABILIZE_CASHFLOW", 0.9, ["CASHFLOW_PRESSURE"]),
    ]
    d = _decide(snapshot=make_snapshot(**SHOCK_SNAPSHOT), moments=moments, intents=intents)
    assert d.primary.journey == JourneyType.CASHFLOW_SUPPORT
    assert d.decision_type == DecisionType.SHOW_WARNING
    sup = {s.journey: s.rule for s in d.suppressed}
    assert sup[JourneyType.INVESTMENT_START] == "CASHFLOW_RISK"


def test_investing_shown_without_cashflow_pressure():
    moments = [make_moment("INVESTMENT_INTEREST", 0.9, days_ago=1, ttl_days=45)]
    intents = [make_intent("START_INVESTING", 0.86, ["INVESTMENT_INTEREST"])]
    d = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents)
    assert d.primary.journey == JourneyType.INVESTMENT_START


def test_not_eligible_investment_with_no_buffer():
    moments = [make_moment("INVESTMENT_INTEREST", 0.9, ttl_days=45)]
    intents = [make_intent("START_INVESTING", 0.9, ["INVESTMENT_INTEREST"])]
    d = _decide(snapshot=make_snapshot(emergency_buffer_months=0.5), moments=moments, intents=intents)
    assert {s.journey: s.rule for s in d.suppressed}[JourneyType.INVESTMENT_START] == "NOT_ELIGIBLE"


def test_not_relevant_feedback_dismisses_journey():
    moments, intents = _first_salary_inputs()
    fb = make_event("RECOMMENDATION_FEEDBACK", {"journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT"}, days_ago=1)
    d = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents, events=[fb])
    assert d.primary is None or d.primary.journey != JourneyType.FINANCIAL_FOUNDATION
    assert {s.journey: s.rule for s in d.suppressed}[JourneyType.FINANCIAL_FOUNDATION] == "FEEDBACK_DISMISSED"


@pytest.mark.parametrize(("days_ago", "wording"), [(0, "today"), (1, "yesterday"), (5, "5 days ago")])
def test_feedback_reason_reads_naturally(days_ago, wording):
    moments, intents = _first_salary_inputs()
    fb = make_event("RECOMMENDATION_FEEDBACK", {"journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT"},
                    days_ago=days_ago)
    d = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents, events=[fb])
    reason = {s.journey: s.reason for s in d.suppressed}[JourneyType.FINANCIAL_FOUNDATION]
    assert reason == f"The customer marked this as not relevant {wording}."


def test_old_or_overridden_feedback_is_ignored():
    moments, intents = _first_salary_inputs()
    old = make_event("RECOMMENDATION_FEEDBACK", {"journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT"}, days_ago=40)
    d = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents, events=[old])
    assert d.primary.journey == JourneyType.FINANCIAL_FOUNDATION
    useful = make_event("RECOMMENDATION_FEEDBACK", {"journey": "FINANCIAL_FOUNDATION", "feedback": "USEFUL"}, days_ago=1)
    recent = make_event("RECOMMENDATION_FEEDBACK", {"journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT"}, days_ago=3)
    d = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents, events=[recent, useful])
    assert d.primary.journey == JourneyType.FINANCIAL_FOUNDATION


def test_later_feedback_is_penalty_only():
    moments, intents = _first_salary_inputs()
    snap = make_snapshot(**FIRST_SALARY_SNAPSHOT)
    base = _decide(snapshot=snap, moments=moments, intents=intents)
    later = make_event("RECOMMENDATION_FEEDBACK", {"journey": "FINANCIAL_FOUNDATION", "feedback": "LATER"}, days_ago=2)
    d = _decide(snapshot=snap, moments=moments, intents=intents, events=[later])
    assert d.primary.journey == JourneyType.FINANCIAL_FOUNDATION
    assert d.primary.breakdown.penalties == 0.25
    assert d.primary.score == pytest.approx(base.primary.score - 0.25, abs=1e-3)
    assert all(s.journey != JourneyType.FINANCIAL_FOUNDATION for s in d.suppressed)


def test_nothing_gives_no_action():
    d = _decide()
    assert d.decision_type == DecisionType.NO_ACTION
    assert d.level == DecisionLevel.NONE and d.primary is None and d.considered == []


def test_only_emerging_moment_gives_wait():
    d = _decide(moments=[make_moment("CAR_PROJECT", 0.25, ttl_days=60)])
    assert d.decision_type == DecisionType.WAIT and d.primary is None
    assert "CAR_PROJECT" in d.reasons[0]


def test_stale_moment_lowers_timing():
    fresh = _decide(moments=[make_moment("TRAVEL", 0.8, ttl_days=30)],
                    intents=[make_intent("PREPARE_TRIP", 0.8, ["TRAVEL"])])
    stale = _decide(moments=[make_moment("TRAVEL", 0.8, days_ago=30, ttl_days=30)],
                    intents=[make_intent("PREPARE_TRIP", 0.8, ["TRAVEL"])])
    assert fresh.primary.breakdown.timing_relevance == 1.0
    assert stale.primary.breakdown.timing_relevance == pytest.approx(0.3)


def test_car_project_covered_insurance_and_eligibility():
    customer = make_customer(products=_products("car_insurance"))
    moments = [make_moment("CAR_PROJECT", 0.85, ttl_days=60)]
    intents = [make_intent("FINANCE_CAR", 0.83, ["CAR_PROJECT"]), make_intent("PROTECT_CAR", 0.34, ["CAR_PROJECT"])]
    d = _decide(customer=customer, moments=moments, intents=intents)
    assert d.primary.journey == JourneyType.CAR_PROJECT
    assert d.decision_type == DecisionType.SHOW_SERVICE
    d = _decide(customer=customer, snapshot=make_snapshot(monthly_income=0), moments=moments, intents=intents)
    assert {s.journey: s.rule for s in d.suppressed}[JourneyType.CAR_PROJECT] == "NOT_ELIGIBLE"


def test_no_consent_suppresses_everything():
    moments, intents = _first_salary_inputs()
    d = _decide(customer=make_customer(consent={"personalization": False}), moments=moments, intents=intents)
    assert d.decision_type == DecisionType.NO_ACTION
    assert d.suppressed and all(s.rule == "NO_CONSENT" for s in d.suppressed)


def test_secondary_is_capped_and_thresholded():
    moments = [make_moment("FIRST_SALARY", 0.95, ttl_days=90), make_moment("TRAVEL", 0.8, ttl_days=30),
               make_moment("CAR_PROJECT", 0.9, ttl_days=60), make_moment("INVESTMENT_INTEREST", 0.9, ttl_days=45)]
    intents = [make_intent("BUILD_FINANCIAL_SAFETY", 0.96, ["FIRST_SALARY"]),
               make_intent("PREPARE_TRIP", 0.8, ["TRAVEL"]),
               make_intent("FINANCE_CAR", 0.9, ["CAR_PROJECT"]),
               make_intent("START_INVESTING", 0.9, ["INVESTMENT_INTEREST"])]
    d = _decide(moments=moments, intents=intents)
    assert len(d.secondary) == 2 and all(c.score >= 0.40 for c in d.secondary)
    assert len(d.considered) == 4


def test_custom_rules_are_injected():
    rules = DECISION_RULES.model_copy(update={"suppression_rules": []})
    moments = [make_moment("INVESTMENT_INTEREST", 0.9, ttl_days=45)]
    intents = [make_intent("START_INVESTING", 0.2, ["INVESTMENT_INTEREST"])]
    d = _decide(moments=moments, intents=intents, engine=DecisionEngine(rules=rules))
    assert d.suppressed == [] and d.considered[0].journey == JourneyType.INVESTMENT_START
    with pytest.raises(ValueError):
        DecisionEngine(rules=DECISION_RULES.model_copy(
            update={"suppression_rules": [SuppressionRule(id="UNKNOWN", description="x")]}))


def test_deterministic():
    moments, intents = _first_salary_inputs()
    a = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents)
    b = _decide(snapshot=make_snapshot(**FIRST_SALARY_SNAPSHOT), moments=moments, intents=intents)
    assert a.model_dump_json() == b.model_dump_json()


def test_no_persona_names_in_t4_code():
    root = Path(__file__).resolve().parents[1] / "app"
    files = [root / "engines" / f for f in ("decision_engine.py", "experience_builder.py", "calculators.py")]
    files += [root / "rules" / f for f in ("decisions.py", "journeys.py", "copy.py")]
    for f in files:
        text = f.read_text().lower()
        for name in ("lucas", "julie", "marc", "claire"):
            assert name not in text, f"{name} in {f.name}"
