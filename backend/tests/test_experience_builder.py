"""Tests for experience_builder. Owner: T4."""

from __future__ import annotations

import json

from conftest import NOW, make_customer, make_event, make_intent, make_moment, make_snapshot

from app.engines.decision_engine import DecisionEngine
from app.engines.experience_builder import ExperienceBuilder
from app.models.common import ActionStatus, DecisionLevel, DecisionType, Evidence, JourneyType
from app.models.context import CustomerContext
from app.models.decision import Decision


def _products(*names):
    return [{"product": n, "since": "2020-01-01"} for n in ("current_account", "savings_account", *names)]


def _run(customer=None, snapshot=None, moments=(), intents=(), events=()):
    customer = customer or make_customer()
    snapshot = snapshot or make_snapshot()
    decision = DecisionEngine().decide(customer, snapshot, list(moments), list(intents), list(events), NOW)
    context = CustomerContext(persistent=customer.profile, products=customer.owned_products(), snapshot=snapshot,
                              signals=[], moments=list(moments))
    return ExperienceBuilder().build(customer, context, list(intents), decision, NOW, events=list(events))


def test_calm_experience():
    exp = _run(snapshot=make_snapshot(emergency_buffer_months=6.3))
    assert exp.mode == "CALM"
    assert exp.hero.title == "Everything looks on track."
    assert exp.hero.tone == "calm"
    assert exp.primary_journey is None and exp.secondary_journeys == []
    assert len(exp.checks) == 5 and all(c.ok for c in exp.checks)
    assert exp.disclaimer.startswith("Amounts are illustrative")


def test_wait_experience_has_calm_hero_and_no_journey():
    moment = make_moment("CAR_PROJECT", 0.25, ttl_days=60)
    moment = moment.model_copy(update={"evidence": [
        Evidence(kind="signal", ref="AUTOMOTIVE_TRANSACTION", contribution=0.25, detail="Payment of €500 at EV dealer"),
    ]})
    exp = _run(moments=[moment])
    assert exp.mode == "WAIT" and exp.hero.tone == "calm" and exp.primary_journey is None
    assert exp.why[0].text == "You made a payment to a car dealer or garage"


def test_family_start_payload_and_hero():
    snapshot = make_snapshot(savings_balance=2_400, monthly_income=3_100, avg_monthly_spending=2_500, monthly_margin=600,
                             emergency_buffer_months=1.1, projected_balance_before_next_income=800)
    moment = make_moment("NEW_PARENT", 0.9, days_ago=10, ttl_days=180).model_copy(update={"evidence": [
        Evidence(kind="signal", ref="PARENTHOOD_DECLARED", contribution=0.55, detail="Declared: expecting a child"),
        Evidence(kind="signal", ref="CHILD_RELATED_EXPENSE", contribution=0.20, detail="Baby supplies"),
    ]})
    intents = [make_intent("CHILD_SAVING", 0.87, ["NEW_PARENT"]),
               make_intent("HOUSEHOLD_BUDGET_ADAPTATION", 0.68, ["NEW_PARENT"]),
               make_intent("FAMILY_PROTECTION", 0.63, ["NEW_PARENT"])]
    customer = make_customer(products=_products("mortgage", "home_insurance"))
    exp = _run(customer=customer, snapshot=snapshot, moments=[moment], intents=intents)
    card = exp.primary_journey
    assert card.type == JourneyType.FAMILY_START
    child = next(a for a in card.actions if a.id == "CHILD_LONG_TERM_SAVINGS")
    assert child.payload["monthly"] == 60
    assert child.payload["progress_without_change"] == 0.21
    assert child.status == ActionStatus.AVAILABLE
    assert exp.hero.type == "NEW_PARENT" and exp.hero.title.startswith("Congratulations")
    assert exp.why[0].text == "You told us you are expecting a child"
    assert exp.mode in ("PROACTIVE", "SUGGESTION")


def test_covered_actions_are_marked_with_reassurance():
    customer = make_customer(products=_products("travel_insurance"))
    exp = _run(customer=customer, moments=[make_moment("TRAVEL", 0.73, ttl_days=30)],
               intents=[make_intent("PREPARE_TRIP", 0.66, ["TRAVEL"])])
    card = exp.primary_journey
    assert card.decision_type == DecisionType.SHOW_SERVICE
    ins = next(a for a in card.actions if a.id == "TRAVEL_INSURANCE")
    assert ins.status == ActionStatus.ALREADY_COVERED
    assert not any(a.status == ActionStatus.AVAILABLE and a.id == "TRAVEL_INSURANCE" for a in card.actions)
    assert any(n.kind == "reassurance" and n.text == "You're already covered for your trip." for n in exp.notices)


def test_uncovered_travel_insurance_is_available():
    exp = _run(moments=[make_moment("TRAVEL", 0.6, ttl_days=30)], intents=[make_intent("PREPARE_TRIP", 0.54, ["TRAVEL"])])
    ins = next(a for a in exp.primary_journey.actions if a.id == "TRAVEL_INSURANCE")
    assert ins.status == ActionStatus.AVAILABLE
    assert next(c for c in exp.checks if c.label == "Protection").ok is False


def test_warning_experience_for_cashflow_support():
    snapshot = make_snapshot(current_balance=1_780, projected_balance_before_next_income=287, avg_monthly_spending=1_600,
                             emergency_buffer_months=1.24)
    exp = _run(snapshot=snapshot, moments=[make_moment("CASHFLOW_PRESSURE", 1.0, ttl_days=14)],
               intents=[make_intent("STABILIZE_CASHFLOW", 0.95, ["CASHFLOW_PRESSURE"])])
    assert exp.hero.tone == "warning" and exp.hero.title == "Heads-up on your balance"
    assert exp.notices[0].kind == "warning"
    forecast = next(a for a in exp.primary_journey.actions if a.id == "CASHFLOW_FORECAST")
    assert forecast.payload["projected_balance"] == 287
    assert next(c for c in exp.checks if c.label == "Balance until next income").ok is False


def test_car_loan_payload_uses_simulation_event():
    customer = make_customer(products=_products("car_insurance"))
    sim = make_event("SIMULATION", {"simulation_type": "electric_car_loan", "amount": 25_000, "duration_months": 60})
    exp = _run(customer=customer, moments=[make_moment("CAR_PROJECT", 0.85, ttl_days=60)],
               intents=[make_intent("FINANCE_CAR", 0.83, ["CAR_PROJECT"])], events=[sim])
    actions = {a.id: a for a in exp.primary_journey.actions}
    assert actions["CAR_INSURANCE_STATUS"].status == ActionStatus.ALREADY_COVERED
    assert actions["CAR_LOAN_SIMULATION"].payload["from_simulation"] is True
    assert actions["CAR_LOAN_SIMULATION"].payload["amount"] == 25_000


def test_no_consent_experience():
    customer = make_customer(consent={"personalization": False})
    decision = Decision(decision_type=DecisionType.NO_ACTION, level=DecisionLevel.NONE, primary=None, secondary=[],
                        considered=[], suppressed=[], reasons=["NO_CONSENT"], decided_at=NOW)
    context = CustomerContext(persistent=customer.profile, products=customer.owned_products(),
                              snapshot=make_snapshot(), signals=[], moments=[])
    exp = ExperienceBuilder().build(customer, context, [], decision, NOW)
    assert exp.mode == "CALM" and exp.hero.type == "NO_CONSENT" and exp.notices[0].kind == "info"


def test_under_the_hood_and_json_serialisable():
    moment = make_moment("FIRST_SALARY", 0.95, days_ago=2, ttl_days=90)
    exp = _run(snapshot=make_snapshot(emergency_buffer_months=2.2), moments=[moment],
               intents=[make_intent("BUILD_FINANCIAL_SAFETY", 0.96, ["FIRST_SALARY"])])
    uth = exp.under_the_hood
    assert uth.decision.primary.journey == JourneyType.FINANCIAL_FOUNDATION
    assert "FIRST_SALARY_expires_at" in uth.timing and "computed_at" in uth.timing
    data = json.loads(exp.model_dump_json())
    assert data["primary_journey"]["actions"]
    assert "<" not in exp.model_dump_json()  # never HTML
