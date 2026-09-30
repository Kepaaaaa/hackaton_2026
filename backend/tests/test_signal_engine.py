"""Tests for signal_engine. Owner: T2."""

from __future__ import annotations

from datetime import timedelta

import pytest
from conftest import NOW, make_customer, make_event, make_snapshot

from app.engines.signal_engine import PATTERN_DETECTORS, SignalEngine
from app.models.common import EventType, SignalType
from app.rules.signals import EVENT_SIGNAL_RULES, SIGNAL_TTL_DAYS

engine = SignalEngine()
customer = make_customer()
healthy = make_snapshot()


def tx(direction: str, amount: float, category: str, days_ago: float = 0, merchant: str = "Shop"):
    return make_event(
        "TRANSACTION",
        {"direction": direction, "amount": amount, "category": category, "merchant": merchant},
        days_ago=days_ago,
    )


def types(signals) -> list[SignalType]:
    return [s.type for s in signals]


def patterns(events, snapshot=healthy) -> dict[SignalType, object]:
    return {s.type: s for s in engine.detect_patterns(customer, events, snapshot, NOW)}


# --- Event rules ------------------------------------------------------------------------

EVENT_CASES = [
    ("TRANSACTION", {"direction": "in", "amount": 2450, "category": "salary", "merchant": "Employer SA"}, SignalType.SALARY_RECEIVED, 1.0),
    ("TRANSACTION", {"direction": "in", "amount": 2450, "category": "pension", "merchant": "Pension Service"}, SignalType.PENSION_RECEIVED, 1.0),
    ("TRANSACTION", {"direction": "in", "amount": 8000, "category": "other_income", "merchant": "Notary"}, SignalType.LARGE_CASH_INFLOW, 1.0),
    ("TRANSACTION", {"direction": "in", "amount": 6000, "category": "refund", "merchant": "Tax office"}, SignalType.LARGE_CASH_INFLOW, 1.0),
    ("TRANSACTION", {"direction": "out", "amount": 420, "category": "airline", "merchant": "Brussels Airlines"}, SignalType.AIR_TRAVEL_ACTIVITY, 0.8),
    ("TRANSACTION", {"direction": "out", "amount": 300, "category": "hotel", "merchant": "Hotel Lisboa"}, SignalType.HOTEL_BOOKING, 0.8),
    ("PAGE_VIEW", {"page": "travel_insurance"}, SignalType.TRAVEL_PAGE_VIEW, 1.0),
    ("PAGE_VIEW", {"page": "card_abroad_settings"}, SignalType.FOREIGN_PAYMENT_SETTINGS_VIEWED, 1.0),
    ("TRANSACTION", {"direction": "out", "amount": 500, "category": "automotive", "merchant": "EV Motors"}, SignalType.AUTOMOTIVE_TRANSACTION, 1.0),
    ("PAGE_VIEW", {"page": "electric_car_loan"}, SignalType.ELECTRIC_CAR_LOAN_PAGE_VIEW, 1.0),
    ("SIMULATION", {"simulation_type": "electric_car_loan", "amount": 25000, "duration_months": 60}, SignalType.ELECTRIC_CAR_LOAN_SIMULATION, 1.0),
    ("KBC_SEARCH", {"query": "electric car loan"}, SignalType.CAR_FINANCING_KBC_SEARCH, 1.0),
    ("KBC_SEARCH", {"query": "Financing my new VEHICLE"}, SignalType.CAR_FINANCING_KBC_SEARCH, 1.0),
    ("PAGE_VIEW", {"page": "mortgage"}, SignalType.MORTGAGE_PAGE_VIEW, 1.0),
    ("SIMULATION", {"simulation_type": "mortgage", "amount": 300000}, SignalType.MORTGAGE_SIMULATION, 1.0),
    ("KBC_SEARCH", {"query": "buy a house"}, SignalType.HOME_KBC_SEARCH, 1.0),
    ("PAGE_VIEW", {"page": "investment_info"}, SignalType.INVESTMENT_PAGE_VIEW, 1.0),
    ("SIMULATION", {"simulation_type": "investment_plan"}, SignalType.INVESTMENT_SIMULATION, 1.0),
    ("KBC_SEARCH", {"query": "start investing"}, SignalType.INVESTMENT_KBC_SEARCH, 1.0),
    ("PAGE_VIEW", {"page": "child_savings"}, SignalType.CHILD_SAVINGS_PAGE_VIEW, 1.0),
    ("PRODUCT_OPENED", {"product": "child_savings_account"}, SignalType.CHILD_ACCOUNT_OPENED, 1.0),
    ("TRANSACTION", {"direction": "out", "amount": 80, "category": "baby_supplies", "merchant": "Baby Shop"}, SignalType.CHILD_RELATED_EXPENSE, 0.6),
    ("TRANSACTION", {"direction": "out", "amount": 400, "category": "childcare", "merchant": "Creche"}, SignalType.CHILD_RELATED_EXPENSE, 0.6),
    ("DECLARED_LIFE_EVENT", {"life_event": "expecting_child"}, SignalType.PARENTHOOD_DECLARED, 1.0),
    ("DECLARED_LIFE_EVENT", {"life_event": "child_born"}, SignalType.PARENTHOOD_DECLARED, 1.0),
    ("DECLARED_LIFE_EVENT", {"life_event": "retiring"}, SignalType.RETIREMENT_DECLARED, 1.0),
    ("PAGE_VIEW", {"page": "retirement_planning"}, SignalType.RETIREMENT_PAGE_VIEW, 1.0),
    ("TRANSACTION", {"direction": "out", "amount": 1500, "category": "unexpected_expense", "merchant": "Garage"}, SignalType.LARGE_UNEXPECTED_EXPENSE, 1.0),
    ("TRANSACTION", {"direction": "out", "amount": 200, "category": "savings_transfer", "merchant": "Own savings"}, SignalType.SAVINGS_TRANSFER, 1.0),
]


@pytest.mark.parametrize(("etype", "data", "expected", "strength"), EVENT_CASES, ids=[c[2].value + "-" + str(i) for i, c in enumerate(EVENT_CASES)])
def test_event_rule_produces_signal(etype, data, expected, strength):
    event = make_event(etype, data, days_ago=3)
    signals = engine.extract(event, NOW)
    assert types(signals) == [expected]
    s = signals[0]
    assert s.strength == strength
    assert s.source == "event"
    assert s.source_event_ids == [event.id]
    assert s.timestamp == event.timestamp
    assert s.expires_at == event.timestamp + timedelta(days=SIGNAL_TTL_DAYS.get(expected, 60))
    assert "3 days ago" in s.description


def test_every_event_rule_is_covered_by_a_test_case():
    assert {r.signal for r in EVENT_SIGNAL_RULES} == {c[2] for c in EVENT_CASES}


@pytest.mark.parametrize(
    ("etype", "data"),
    [
        ("TRANSACTION", {"direction": "out", "amount": 60, "category": "groceries", "merchant": "Delhaize"}),
        ("TRANSACTION", {"direction": "in", "amount": 420, "category": "airline", "merchant": "Refund"}),  # wrong direction
        ("TRANSACTION", {"direction": "out", "amount": 499.99, "category": "unexpected_expense", "merchant": "Plumber"}),
        ("TRANSACTION", {"direction": "in", "amount": 4999, "category": "other_income", "merchant": "Gift"}),
        ("PAGE_VIEW", {"page": "budgeting_tools"}),
        ("KBC_SEARCH", {"query": "every loan option"}),  # "ev" must match a whole word only
        ("KBC_SEARCH", {"query": "car insurance"}),  # car but no financing keyword
        ("DECLARED_LIFE_EVENT", {"life_event": "moving"}),
        ("RECOMMENDATION_FEEDBACK", {"journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT"}),
        ("JOURNEY_INTERACTION", {"journey": "FINANCIAL_FOUNDATION", "action_id": "OPEN_SAVINGS"}),
    ],
)
def test_non_matching_events_produce_no_signal(etype, data):
    assert engine.extract(make_event(etype, data), NOW) == []


def test_single_airline_payment_is_ambiguous():
    """Anti-example from the brief: one airline payment is a weak signal, not a trip."""
    signals = engine.extract_all(customer, [tx("out", 420, "airline", merchant="Brussels Airlines")], healthy, NOW)
    assert types(signals) == [SignalType.AIR_TRAVEL_ACTIVITY]
    assert signals[0].strength < 1.0
    assert signals[0].source == "event"


def test_description_is_human_and_never_contains_search_query():
    airline = engine.extract(tx("out", 420, "airline", days_ago=12, merchant="Brussels Airlines"), NOW)[0]
    assert airline.description == "Airline payment of €420 at Brussels Airlines, 12 days ago"
    search = engine.extract(make_event("KBC_SEARCH", {"query": "secret electric car loan xyz"}), NOW)[0]
    assert search.description == "KBC search about car financing, today"
    assert "secret" not in search.description and "xyz" not in search.description


def test_custom_rules_are_injectable():
    from app.rules.schema import DataMatch, SignalEventRule

    rule = SignalEventRule(
        event_type=EventType.PAGE_VIEW,
        match=[DataMatch(field="page", value="budgeting_tools")],
        signal=SignalType.SAVINGS_TRANSFER,
        strength=0.5,
        ttl_days=7,
    )
    signals = SignalEngine(rules=[rule]).extract(make_event("PAGE_VIEW", {"page": "budgeting_tools"}), NOW)
    assert types(signals) == [SignalType.SAVINGS_TRANSFER]
    assert signals[0].expires_at == NOW + timedelta(days=7)
    assert signals[0].description == "Savings transfer, today"


# --- Patterns -------------------------------------------------------------------------------


def test_first_recurring_salary_positive():
    events = [tx("in", 300, "other_income", days_ago=100), tx("in", 2450, "salary", days_ago=2)]
    hit = patterns(events)[SignalType.FIRST_RECURRING_SALARY]
    assert hit.strength == 1.0
    assert hit.source == "pattern"
    assert hit.timestamp == NOW - timedelta(days=2)
    assert len(hit.source_event_ids) == 1


def test_first_recurring_salary_negative_when_salary_before():
    events = [tx("in", 2450, "salary", days_ago=33), tx("in", 2450, "salary", days_ago=2)]
    assert SignalType.FIRST_RECURRING_SALARY not in patterns(events)


def test_first_recurring_salary_negative_without_recent_salary():
    assert SignalType.FIRST_RECURRING_SALARY not in patterns([tx("in", 2450, "salary", days_ago=40)])


def test_salary_stopped_positive():
    events = [tx("in", 3000, "salary", days_ago=d) for d in (165, 135, 105, 75)]
    hit = patterns(events)[SignalType.SALARY_STOPPED]
    assert hit.timestamp == NOW - timedelta(days=30)  # 75 days ago + 45 quiet days
    assert len(hit.source_event_ids) == 4


def test_salary_stopped_negative_when_salary_continues():
    events = [tx("in", 3000, "salary", days_ago=d) for d in (95, 65, 35, 5)]
    assert SignalType.SALARY_STOPPED not in patterns(events)


def test_recurring_pension_started_positive_and_negative():
    new = [tx("in", 2450, "pension", days_ago=d) for d in (40, 10)]
    hit = patterns(new)[SignalType.RECURRING_PENSION_STARTED]
    assert hit.timestamp == NOW - timedelta(days=40)
    assert len(hit.source_event_ids) == 2
    old = [tx("in", 2450, "pension", days_ago=d) for d in (100, 70, 40, 10)]
    assert SignalType.RECURRING_PENSION_STARTED not in patterns(old)


def test_new_recurring_child_expenses_positive():
    events = [tx("out", 60, "baby_supplies", days_ago=d) for d in (25, 15, 5)]
    hit = patterns(events)[SignalType.NEW_RECURRING_CHILD_EXPENSES]
    assert hit.strength == 0.8
    assert hit.timestamp == NOW - timedelta(days=5)


def test_new_recurring_child_expenses_negative():
    two = [tx("out", 60, "baby_supplies", days_ago=d) for d in (15, 5)]
    assert SignalType.NEW_RECURRING_CHILD_EXPENSES not in patterns(two)
    with_older = two + [tx("out", 60, "childcare", days_ago=d) for d in (20, 90)]
    assert SignalType.NEW_RECURRING_CHILD_EXPENSES not in patterns(with_older)


def test_repeated_mortgage_simulation():
    sims = [make_event("SIMULATION", {"simulation_type": "mortgage"}, days_ago=d) for d in (20, 10, 1)]
    assert SignalType.REPEATED_MORTGAGE_SIMULATION in patterns(sims)
    assert SignalType.REPEATED_MORTGAGE_SIMULATION not in patterns(sims[:2])
    spread = [make_event("SIMULATION", {"simulation_type": "mortgage"}, days_ago=d) for d in (50, 10, 1)]
    assert SignalType.REPEATED_MORTGAGE_SIMULATION not in patterns(spread)


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"projected_balance_before_next_income": 287.0, "avg_monthly_spending": 1600.0}, True),
        ({"projected_balance_before_next_income": 800.0, "avg_monthly_spending": 3000.0}, True),  # < 0.3 x spending
        ({"projected_balance_before_next_income": 1787.0, "avg_monthly_spending": 1600.0}, False),
    ],
)
def test_low_projected_balance(overrides, expected):
    assert (SignalType.LOW_PROJECTED_BALANCE in patterns([], make_snapshot(**overrides))) is expected


def test_low_emergency_buffer():
    assert SignalType.LOW_EMERGENCY_BUFFER in patterns([], make_snapshot(emergency_buffer_months=2.2))
    assert SignalType.LOW_EMERGENCY_BUFFER not in patterns([], make_snapshot(emergency_buffer_months=6.3))


def test_high_idle_cash():
    assert SignalType.HIGH_IDLE_CASH in patterns([], make_snapshot(idle_cash=40000.0, idle_ratio=0.74))
    assert SignalType.HIGH_IDLE_CASH not in patterns([], make_snapshot(idle_cash=40000.0, idle_ratio=0.3))
    assert SignalType.HIGH_IDLE_CASH not in patterns([], make_snapshot(idle_cash=9000.0, idle_ratio=0.9))


def test_snapshot_patterns_are_timestamped_now_without_source_events():
    s = patterns([], make_snapshot(emergency_buffer_months=1.0))[SignalType.LOW_EMERGENCY_BUFFER]
    assert s.timestamp == NOW
    assert s.source_event_ids == []


def test_healthy_customer_has_no_pattern_signal():
    events = [tx("in", 3900, "salary", days_ago=d) for d in range(5, 400, 30)]
    assert patterns(events) == {}


def test_pattern_detectors_cover_every_pattern_signal():
    assert set(PATTERN_DETECTORS) == {
        SignalType.FIRST_RECURRING_SALARY,
        SignalType.SALARY_STOPPED,
        SignalType.RECURRING_PENSION_STARTED,
        SignalType.NEW_RECURRING_CHILD_EXPENSES,
        SignalType.REPEATED_MORTGAGE_SIMULATION,
        SignalType.LOW_PROJECTED_BALANCE,
        SignalType.LOW_EMERGENCY_BUFFER,
        SignalType.HIGH_IDLE_CASH,
    }


# --- extract_all ------------------------------------------------------------------------------


def test_extract_all_drops_expired_signals():
    events = [
        tx("out", 420, "airline", days_ago=40),  # TTL 30 -> expired
        make_event("PAGE_VIEW", {"page": "investment_info"}, days_ago=59),  # TTL 60 -> still active
        make_event("PAGE_VIEW", {"page": "mortgage"}, days_ago=61),  # expired
    ]
    assert types(engine.extract_all(customer, events, healthy, NOW)) == [SignalType.INVESTMENT_PAGE_VIEW]


def test_extract_all_combines_event_and_pattern_signals_sorted():
    events = [tx("in", 2450, "salary", days_ago=2), make_event("PAGE_VIEW", {"page": "investment_info"}, days_ago=5)]
    signals = engine.extract_all(customer, events, make_snapshot(emergency_buffer_months=2.2), NOW)
    assert types(signals) == [
        SignalType.INVESTMENT_PAGE_VIEW,
        SignalType.FIRST_RECURRING_SALARY,
        SignalType.SALARY_RECEIVED,
        SignalType.LOW_EMERGENCY_BUFFER,
    ]
    assert [s.timestamp for s in signals] == sorted(s.timestamp for s in signals)


def test_extract_all_is_deterministic():
    events = [tx("in", 2450, "salary", days_ago=2), tx("out", 1500, "unexpected_expense")]
    snap = make_snapshot(projected_balance_before_next_income=287.0)
    assert engine.extract_all(customer, events, snap, NOW) == engine.extract_all(customer, list(reversed(events)), snap, NOW)


def test_lucas_like_cashflow_shock_end_to_end():
    """Snapshot + signals: a live -€1,500 shock turns into LOW_PROJECTED_BALANCE + LARGE_UNEXPECTED_EXPENSE."""
    from app.engines.financial_snapshot import compute_snapshot
    from test_financial_snapshot import lucas_like

    lucas, events = lucas_like()
    before = engine.extract_all(lucas, events, compute_snapshot(lucas, events, NOW), NOW)
    assert SignalType.LOW_PROJECTED_BALANCE not in types(before)
    assert {SignalType.FIRST_RECURRING_SALARY, SignalType.LOW_EMERGENCY_BUFFER} <= set(types(before))

    events.append(make_event(
        "TRANSACTION",
        {"direction": "out", "amount": 1500, "category": "unexpected_expense", "merchant": "Garage"},
        origin="live",
    ))
    after = engine.extract_all(lucas, events, compute_snapshot(lucas, events, NOW), NOW)
    assert {SignalType.LOW_PROJECTED_BALANCE, SignalType.LARGE_UNEXPECTED_EXPENSE} <= set(types(after))
