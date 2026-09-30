"""Frozen contracts: validation of events, customers and rule schemas. Owner: T0."""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from conftest import NOW, make_customer, make_event, make_intent, make_moment, make_signal, make_snapshot
from pydantic import ValidationError

from app.models.common import EventType, MomentStatus
from app.models.event import CustomerEventAdapter, EventInputAdapter, TransactionEvent
from app.rules.schema import Condition, DataMatch, IntentRule, ProfileAdjustment


def _tx_input(**data_overrides):
    data = {"direction": "out", "amount": 42.5, "category": "groceries", "merchant": "Delhaize"}
    data.update(data_overrides)
    return {"type": "TRANSACTION", "data": data}


# --- Events -------------------------------------------------------------------------


def test_valid_transaction_event_input():
    event_input = EventInputAdapter.validate_python(_tx_input())
    assert event_input.days_ago == 0
    assert event_input.data.amount == 42.5


def test_each_event_type_accepts_valid_input():
    samples = [
        _tx_input(),
        {"type": "PAGE_VIEW", "data": {"page": "electric_car_loan"}},
        {"type": "SIMULATION", "data": {"simulation_type": "electric_car_loan", "amount": 25000, "duration_months": 60}},
        {"type": "KBC_SEARCH", "data": {"query": "electric car loan"}},
        {"type": "PRODUCT_OPENED", "data": {"product": "child_savings_account"}},
        {"type": "DECLARED_LIFE_EVENT", "data": {"life_event": "expecting_child"}},
        {"type": "RECOMMENDATION_FEEDBACK", "data": {"journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT"}},
        {"type": "JOURNEY_INTERACTION", "data": {"journey": "CAR_PROJECT", "action_id": "CAR_LOAN_SIMULATION"}},
    ]
    parsed = [EventInputAdapter.validate_python(s) for s in samples]
    assert [p.type for p in parsed] == [EventType(s["type"]) for s in samples]


def test_extra_field_rejected():
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python({**_tx_input(), "admin": True})
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python(_tx_input(evil="x"))


def test_client_cannot_set_server_fields():
    for field, value in [("id", "evt_x"), ("customer_id", "lucas"), ("timestamp", NOW.isoformat()), ("origin", "seed")]:
        with pytest.raises(ValidationError):
            EventInputAdapter.validate_python({**_tx_input(), field: value})


@pytest.mark.parametrize("amount", [-10, 0, 1_000_001])
def test_bad_amount_rejected(amount):
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python(_tx_input(amount=amount))


def test_amount_rounded_to_cents():
    event_input = EventInputAdapter.validate_python(_tx_input(amount=10.456))
    assert event_input.data.amount == 10.46


def test_bad_page_rejected():
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python({"type": "PAGE_VIEW", "data": {"page": "www.competitor.com"}})


def test_bad_event_type_rejected():
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python({"type": "WEB_BROWSING", "data": {}})


def test_search_query_limits():
    ok = EventInputAdapter.validate_python({"type": "KBC_SEARCH", "data": {"query": "  " + "a" * 100 + "  "}})
    assert ok.data.query == "a" * 100
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python({"type": "KBC_SEARCH", "data": {"query": "a" * 101}})
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python({"type": "KBC_SEARCH", "data": {"query": "   "}})
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python({"type": "KBC_SEARCH", "data": {"query": "car\x00loan"}})


def test_control_chars_in_merchant_rejected():
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python(_tx_input(merchant="Shop\nInjected"))


@pytest.mark.parametrize("days_ago", [-1, 366])
def test_days_ago_bounded(days_ago):
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python({**_tx_input(), "days_ago": days_ago})


def test_simulation_bounds():
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python({"type": "SIMULATION", "data": {"simulation_type": "mortgage", "duration_months": 481}})


def test_journey_interaction_action_id_pattern():
    with pytest.raises(ValidationError):
        EventInputAdapter.validate_python(
            {"type": "JOURNEY_INTERACTION", "data": {"journey": "CAR_PROJECT", "action_id": "<script>"}}
        )


def test_to_event_applies_days_ago_and_server_fields():
    event_input = EventInputAdapter.validate_python({**_tx_input(), "days_ago": 3})
    event = event_input.to_event("lucas", NOW, "evt_lucas_live_1")
    assert isinstance(event, TransactionEvent)
    assert event.timestamp == NOW - timedelta(days=3)
    assert event.origin == "live"
    assert event.customer_id == "lucas"
    assert event.id == "evt_lucas_live_1"


def test_stored_event_round_trip_and_requires_timezone():
    event = make_event("PAGE_VIEW", {"page": "mortgage"}, days_ago=2)
    again = CustomerEventAdapter.validate_json(CustomerEventAdapter.dump_json(event))
    assert again == event
    raw = json.loads(CustomerEventAdapter.dump_json(event))
    raw["timestamp"] = "2026-10-01T09:00:00"  # naive
    with pytest.raises(ValidationError):
        CustomerEventAdapter.validate_python(raw)


# --- Customers ------------------------------------------------------------------------


def test_valid_customer():
    customer = make_customer()
    assert customer.consent.personalization is True
    assert "current_account" in customer.owned_products()


@pytest.mark.parametrize("bad_id", ["Lucas", "1abc", "a", "a" * 33, "lu cas", "../etc", "lucas;drop"])
def test_bad_customer_id_rejected(bad_id):
    with pytest.raises(ValidationError):
        make_customer(id=bad_id)


def test_customer_extra_field_rejected():
    with pytest.raises(ValidationError):
        make_customer(segment="young")


# --- Rule schema ------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["age", "age_bucket", "age.years"])
def test_age_profile_adjustment_rejected(path):
    with pytest.raises(ValidationError):
        ProfileAdjustment(path=path, equals=30, delta=0.1)
    with pytest.raises(ValidationError):
        IntentRule(intent="START_SAVING", profile_adjustments=[{"path": path, "equals": 30, "delta": 0.1}])


def test_valid_profile_adjustment():
    adj = ProfileAdjustment(path="financial_profile.financial_maturity", equals="beginner", delta=0.1)
    assert adj.delta == 0.1


def test_condition_evaluate():
    snapshot = make_snapshot(monthly_income=0.0).model_dump()
    assert Condition(field="monthly_income", op="gt", value=0).evaluate(snapshot, []) is False
    assert Condition(field="emergency_buffer_months", op="ge", value=1).evaluate(snapshot, []) is True
    assert Condition(op="owns", value="car_insurance").evaluate(snapshot, ["car_insurance"]) is True
    assert Condition(op="not_owns", value="car_insurance").evaluate(snapshot, ["car_insurance"]) is False
    with pytest.raises(ValidationError):
        Condition(op="owns", value="spaceship")
    with pytest.raises(ValidationError):
        Condition(op="gt", value=0)


def test_data_match_op_value_consistency():
    DataMatch(field="page", op="in", value=["travel_insurance"])
    with pytest.raises(ValidationError):
        DataMatch(field="page", op="in", value="travel_insurance")
    with pytest.raises(ValidationError):
        DataMatch(field="amount", op="ge", value=["500"])


# --- Builders -----------------------------------------------------------------------------


def test_builders_produce_valid_models():
    signal = make_signal("AIR_TRAVEL_ACTIVITY", 0.8, days_ago=5)
    assert signal.expires_at == signal.timestamp + timedelta(days=60)
    assert make_moment("CAR_PROJECT", 0.25).status == MomentStatus.EMERGING
    assert make_moment("CAR_PROJECT", 0.55).status == MomentStatus.ACTIVE
    assert make_intent("START_SAVING", 0.7).confidence == 0.7
    assert make_snapshot(current_balance=1.0).current_balance == 1.0
