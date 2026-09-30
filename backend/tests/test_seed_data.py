"""Seed data: validity, persona facts, and snapshot figures hand-computed with A.9. Owner: T1.

Formulas are re-implemented here on purpose (we do not import T2's engine).
"""

from __future__ import annotations

import json
import re
from datetime import timedelta

import pytest
from conftest import NOW

from app.models.common import EventType
from app.models.event import TransactionEvent
from app.repositories import seed_loader
from app.repositories.seed_loader import load_seed, scenario_step_events

EXCLUDED_FROM_SPENDING = {"savings_transfer", "investment", "unexpected_expense"}


@pytest.fixture(scope="module")
def seed():
    return load_seed(NOW)


def _customer(seed, cid):
    return next(c for c in seed.customers if c.id == cid)


def _tx(seed, cid, category=None, direction=None):
    return [
        e
        for e in seed.events_by_customer[cid]
        if isinstance(e, TransactionEvent)
        and (category is None or e.data.category == category)
        and (direction is None or e.data.direction == direction)
    ]


def _days_ago(e) -> float:
    return (NOW - e.timestamp) / timedelta(days=1)


def snapshot(seed, cid) -> dict[str, float]:
    customer = _customer(seed, cid)
    current = sum(a.balance for a in customer.accounts if a.type == "current")
    savings = sum(a.balance for a in customer.accounts if a.type == "savings")
    liquid = current + savings
    spending = sum(
        e.data.amount
        for e in _tx(seed, cid, direction="out")
        if _days_ago(e) <= 90 and e.data.category not in EXCLUDED_FROM_SPENDING
    ) / 3
    income_tx = [e for e in _tx(seed, cid, direction="in") if e.data.category in ("salary", "pension")]
    monthly_income = sum(e.data.amount for e in income_tx if _days_ago(e) <= 30)
    latest = max(e.timestamp for e in income_tx)
    days_until = min(30, max(0, ((latest + timedelta(days=30)).date() - NOW.date()).days))
    idle = max(0.0, liquid - 6 * spending)
    return {
        "current": current,
        "savings": savings,
        "liquid": liquid,
        "spending": spending,
        "monthly_income": monthly_income,
        "days_until": days_until,
        "projected": current - spending * days_until / 30,
        "buffer": (savings + max(0.0, current - spending)) / spending,
        "idle": idle,
        "idle_ratio": idle / liquid,
    }


# --- validity ---------------------------------------------------------------------


def test_four_personas_with_consent(seed):
    assert sorted(c.id for c in seed.customers) == ["claire", "julie", "lucas", "marc"]
    assert all(c.consent.personalization for c in seed.customers)
    assert set(seed.events_by_customer) == {c.id for c in seed.customers}


def test_event_ids_unique_deterministic_and_seed_origin(seed):
    all_events = [e for evs in seed.events_by_customer.values() for e in evs]
    ids = [e.id for e in all_events]
    assert len(ids) == len(set(ids))
    assert all(e.origin == "seed" for e in all_events)
    assert [e.id for e in load_seed(NOW).events_by_customer["lucas"]] == [
        e.id for e in seed.events_by_customer["lucas"]
    ]
    for cid, evs in seed.events_by_customer.items():
        assert all(e.customer_id == cid and e.id.startswith(f"evt_{cid}_") for e in evs)


def test_events_chronological_in_past_and_within_history(seed):
    for evs in seed.events_by_customer.values():
        stamps = [e.timestamp for e in evs]
        assert stamps == sorted(stamps)
        assert all(ts <= NOW and ts.tzinfo is not None for ts in stamps)
        assert 90 <= _days_ago(evs[0]) <= 200


def test_relative_time_moves_with_now(seed):
    later = load_seed(NOW + timedelta(days=100))
    a, b = seed.events_by_customer["julie"], later.events_by_customer["julie"]
    assert [(y.timestamp - x.timestamp).days for x, y in zip(a, b, strict=True)] == [100] * len(a)


def test_accounts_masked_and_fake():
    raw = json.loads(seed_loader.CUSTOMERS_FILE.read_text(encoding="utf-8"))
    for c in raw:
        for acc in c["accounts"]:
            assert acc["masked_number"].startswith("•••• ") and len(acc["masked_number"]) == 9


def test_no_outcome_hints_in_data():
    for path in (seed_loader.CUSTOMERS_FILE, seed_loader.EVENTS_FILE):
        text = path.read_text(encoding="utf-8").lower()
        for hint in ("expected", "moment", "intent", "journey", "persona"):
            assert not re.search(rf"\b{hint}s?\b", text), (path.name, hint)


def test_loader_fails_loudly_on_invalid_data(tmp_path, monkeypatch):
    bad = json.loads(seed_loader.EVENTS_FILE.read_text(encoding="utf-8"))
    bad["lucas"][0]["data"]["amount"] = -5
    path = tmp_path / "events.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    monkeypatch.setattr(seed_loader, "EVENTS_FILE", path)
    with pytest.raises(ValueError):
        load_seed(NOW)


# --- persona facts ----------------------------------------------------------------


def test_lucas_single_first_salary(seed):
    salaries = _tx(seed, "lucas", "salary")
    assert len(salaries) == 1
    assert salaries[0].data.amount == 2450 and salaries[0].data.merchant == "Employer SA"
    assert 1.5 <= _days_ago(salaries[0]) <= 2.5
    assert _tx(seed, "lucas", "other_income", "in"), "past student-job income expected"
    owned = _customer(seed, "lucas").owned_products()
    assert "travel_insurance" not in owned and "pension_savings" not in owned


def test_marc_salary_stops_then_pension_starts(seed):
    salaries = [_days_ago(e) for e in _tx(seed, "marc", "salary")]
    pensions = [_days_ago(e) for e in _tx(seed, "marc", "pension")]
    assert min(salaries) > 45 and any(60 <= d <= 180 for d in salaries)
    assert len(pensions) == 2 and all(d <= 45 for d in pensions)
    assert all(e.data.amount == 2450 for e in _tx(seed, "marc", "pension"))
    assert max(pensions) < min(salaries)
    assert [a.type for a in _customer(seed, "marc").accounts] == ["current"]


def test_julie_declared_parenthood_then_child_signals(seed):
    evs = seed.events_by_customer["julie"]
    declared = [e for e in evs if e.type == EventType.DECLARED_LIFE_EVENT]
    assert len(declared) == 1 and declared[0].data.life_event == "expecting_child"
    assert 9.5 <= _days_ago(declared[0]) <= 10.5
    baby = _tx(seed, "julie", "baby_supplies", "out")
    assert len(baby) == 3 and all(declared[0].timestamp < e.timestamp and _days_ago(e) <= 30 for e in baby)
    pages = [e for e in evs if e.type == EventType.PAGE_VIEW]
    assert [p.data.page for p in pages] == ["child_savings"] and 2.5 <= _days_ago(pages[0]) <= 3.5
    assert len(_tx(seed, "julie", "mortgage_payment")) >= 3
    owned = _customer(seed, "julie").owned_products()
    assert "child_savings_account" not in owned and "family_insurance" not in owned


def test_claire_well_covered_and_only_routine(seed):
    owned = set(_customer(seed, "claire").owned_products())
    assert {"travel_insurance", "car_insurance", "family_insurance", "pension_savings",
            "investment_plan", "child_savings_account"} <= owned
    evs = seed.events_by_customer["claire"]
    assert {e.type for e in evs} == {EventType.TRANSACTION}
    forbidden = {"airline", "hotel", "automotive", "childcare", "baby_supplies", "unexpected_expense",
                 "other_income", "refund", "pension"}
    assert not [e for e in evs if e.data.category in forbidden]
    salaries = _tx(seed, "claire", "salary")
    assert len(salaries) >= 6 and all(e.data.amount == 3900 for e in salaries)


# --- snapshot figures (A.9 by hand) -------------------------------------------------


def test_lucas_snapshot(seed):
    s = snapshot(seed, "lucas")
    assert (s["current"], s["savings"]) == (3280, 1800)
    assert 1550 <= s["spending"] <= 1650
    assert s["monthly_income"] == 2450 and s["days_until"] == 28
    assert s["buffer"] == pytest.approx(2.2, abs=0.05)
    assert s["projected"] == pytest.approx(1787, abs=5)
    assert s["projected"] - 1500 == pytest.approx(287, abs=5)  # after the cashflow_shock scenario


def test_julie_snapshot(seed):
    s = snapshot(seed, "julie")
    assert (s["current"], s["savings"]) == (2900, 2400)
    assert s["spending"] == pytest.approx(2500, abs=10)
    assert s["monthly_income"] == 3100
    assert s["projected"] > 500


def test_marc_snapshot(seed):
    s = snapshot(seed, "marc")
    assert (s["current"], s["savings"]) == (54400, 0)
    assert s["spending"] == pytest.approx(2400, abs=10)
    assert s["monthly_income"] == 2450
    assert s["idle"] == pytest.approx(40000, abs=100)
    assert s["idle_ratio"] == pytest.approx(0.74, abs=0.01)


def test_claire_snapshot(seed):
    s = snapshot(seed, "claire")
    assert (s["current"], s["savings"]) == (4000, 18000)
    assert s["spending"] == pytest.approx(3000, abs=10)
    assert s["buffer"] >= 6
    assert s["idle"] < 10000
    assert s["projected"] > 500


# --- scenarios ----------------------------------------------------------------------


def test_scenarios_match_a4(seed):
    by_id = {s.id: s for s in seed.scenarios}
    assert set(by_id) == {"electric_car", "travel_covered", "travel_uncovered", "cashflow_shock", "not_relevant"}
    expected_customer = {"electric_car": "claire", "travel_covered": "claire", "travel_uncovered": "lucas",
                         "cashflow_shock": "lucas", "not_relevant": "lucas"}
    assert {k: s.customer_id for k, s in by_id.items()} == expected_customer
    assert len(by_id["electric_car"].steps) == 4
    assert len(by_id["cashflow_shock"].steps) == 2


def test_scenario_step_events_helper():
    step = scenario_step_events("electric_car", 2)
    assert len(step) == 1 and step[0].type == EventType.SIMULATION
    assert (step[0].data.amount, step[0].data.duration_months) == (25000, 60)
    shock = scenario_step_events("cashflow_shock", 1)[0]
    assert shock.data.category == "unexpected_expense" and shock.data.amount == 1500
    event = shock.to_event("lucas", NOW, "evt_live_1")
    assert event.origin == "live" and event.timestamp == NOW
    step[0].data.amount = 1  # returned copies must not leak into the cache
    assert scenario_step_events("electric_car", 2)[0].data.amount == 25000
    with pytest.raises(KeyError):
        scenario_step_events("nope", 0)
    with pytest.raises(IndexError):
        scenario_step_events("electric_car", 4)
    with pytest.raises(IndexError):
        scenario_step_events("electric_car", -1)
