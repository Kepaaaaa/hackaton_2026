"""Tests for financial_snapshot. Owner: T2."""

from __future__ import annotations

from datetime import timedelta

import pytest
from conftest import NOW, make_customer, make_event

from app.engines.financial_snapshot import compute_snapshot


def tx(direction: str, amount: float, category: str, days_ago: float = 0, origin: str = "seed", merchant: str = "Shop"):
    return make_event(
        "TRANSACTION",
        {"direction": direction, "amount": amount, "category": category, "merchant": merchant},
        days_ago=days_ago,
        origin=origin,
    )


def accounts(current: float, savings: float | None = None) -> list[dict]:
    accs = [{"id": "c", "type": "current", "label": "Current", "masked_number": "•••• 0001", "balance": current}]
    if savings is not None:
        accs.append({"id": "s", "type": "savings", "label": "Savings", "masked_number": "•••• 0002", "balance": savings})
    return accs


def lucas_like():
    """Lucas-like: €3,280 current, €1,800 savings, first salary 2 days ago, €1,600/month spending."""
    customer = make_customer(accounts=accounts(3280.0, 1800.0))
    events = [tx("in", 2450.0, "salary", days_ago=2, merchant="Employer SA")]
    for month in range(3):
        events.append(tx("out", 750.0, "rent", days_ago=5 + 30 * month))
        events.append(tx("out", 850.0, "groceries", days_ago=10 + 30 * month))
    return customer, events


def test_lucas_like_projection_and_buffer():
    customer, events = lucas_like()
    s = compute_snapshot(customer, events, NOW)
    assert s.avg_monthly_spending == 1600.0
    assert s.monthly_income == 2450.0
    assert s.income_sources == ["salary"]
    assert s.next_income_date == (NOW - timedelta(days=2) + timedelta(days=30)).date()
    assert s.days_until_next_income == 28
    assert s.projected_balance_before_next_income == pytest.approx(1786.67, abs=0.01)
    assert s.emergency_buffer_months == pytest.approx(2.175, abs=0.001)
    assert s.monthly_margin == 850.0


def test_live_unexpected_expense_shifts_current_balance():
    customer, events = lucas_like()
    events.append(tx("out", 1500.0, "unexpected_expense", origin="live", merchant="Garage"))
    s = compute_snapshot(customer, events, NOW)
    assert s.current_balance == 1780.0
    assert s.liquid_balance == 3580.0
    assert s.avg_monthly_spending == 1600.0  # unexpected_expense excluded from spending
    assert s.projected_balance_before_next_income == pytest.approx(286.67, abs=0.01)


def test_seed_transactions_do_not_change_balance_but_live_ones_do():
    customer = make_customer(accounts=accounts(1000.0))
    seed = [tx("out", 200.0, "groceries", days_ago=3)]
    live = [tx("in", 50.0, "refund", origin="live"), tx("out", 20.0, "leisure", origin="live")]
    assert compute_snapshot(customer, seed, NOW).current_balance == 1000.0
    assert compute_snapshot(customer, seed + live, NOW).current_balance == 1030.0


def test_spending_excludes_transfers_and_old_transactions():
    customer = make_customer(accounts=accounts(5000.0))
    events = [
        tx("out", 300.0, "groceries", days_ago=10),
        tx("out", 1000.0, "savings_transfer", days_ago=10),
        tx("out", 1000.0, "investment", days_ago=10),
        tx("out", 900.0, "unexpected_expense", days_ago=10),
        tx("out", 5000.0, "groceries", days_ago=95),  # outside the 90-day window
    ]
    assert compute_snapshot(customer, events, NOW).avg_monthly_spending == 100.0


def test_income_uses_last_30_days_of_salary_and_pension():
    customer = make_customer(accounts=accounts(1000.0))
    events = [
        tx("in", 1000.0, "salary", days_ago=5),
        tx("in", 500.0, "pension", days_ago=20),
        tx("in", 999.0, "salary", days_ago=40),
        tx("in", 300.0, "other_income", days_ago=3),
    ]
    s = compute_snapshot(customer, events, NOW)
    assert s.monthly_income == 1500.0
    assert s.income_sources == ["pension", "salary"]
    assert s.days_until_next_income == 25


def test_idle_cash_marc_like():
    customer = make_customer(accounts=accounts(54400.0))
    events = [tx("in", 2450.0, "pension", days_ago=10)]
    events += [tx("out", 2400.0, "other", days_ago=5 + 30 * m) for m in range(3)]
    s = compute_snapshot(customer, events, NOW)
    assert s.idle_cash == 40000.0
    assert s.idle_ratio == pytest.approx(0.7353, abs=0.0001)


def test_debt_payments_and_ratio():
    customer = make_customer(accounts=accounts(2000.0))
    events = [
        tx("in", 3000.0, "salary", days_ago=5),
        tx("out", 900.0, "mortgage_payment", days_ago=3),
        tx("out", 300.0, "loan_repayment", days_ago=4),
        tx("out", 900.0, "mortgage_payment", days_ago=33),
    ]
    s = compute_snapshot(customer, events, NOW)
    assert s.monthly_debt_payments == 1200.0
    assert s.debt_ratio == 0.4


def test_next_income_date_is_clamped_to_zero_when_overdue():
    customer = make_customer(accounts=accounts(1000.0))
    s = compute_snapshot(customer, [tx("in", 1000.0, "salary", days_ago=50)], NOW)
    assert s.days_until_next_income == 0
    assert s.projected_balance_before_next_income == 1000.0


def test_no_income_no_spending_edge_case():
    customer = make_customer(accounts=accounts(0.0))
    s = compute_snapshot(customer, [], NOW)
    assert s.monthly_income == 0.0
    assert s.income_sources == []
    assert s.next_income_date is None
    assert s.days_until_next_income == 30
    assert s.avg_monthly_spending == 0.0
    assert s.emergency_buffer_months == 0.0
    assert s.idle_ratio == 0.0
    assert s.debt_ratio == 0.0


def test_future_events_are_ignored():
    customer = make_customer(accounts=accounts(1000.0))
    s = compute_snapshot(customer, [tx("out", 500.0, "groceries", days_ago=-2, origin="live")], NOW)
    assert s.current_balance == 1000.0
    assert s.avg_monthly_spending == 0.0
