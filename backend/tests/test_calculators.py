"""Tests for calculators. Owner: T4."""

from __future__ import annotations

import pytest
from conftest import make_event, make_snapshot

from app.engines.calculators import (
    cashflow_forecast,
    emergency_buffer_goal,
    idle_cash_insight,
    loan_monthly_payment,
    monthly_for_target,
    run_calculator,
)


def test_monthly_for_target_pension_check_values():
    p = monthly_for_target(1_800, 100_000, 40 * 12, monthly_margin=850)
    assert p["monthly"] == 110
    assert p["progress_without_change"] == 0.06
    assert p["capped"] is False


def test_monthly_for_target_child_check_values():
    p = monthly_for_target(2_400, 20_000, 18 * 12, monthly_margin=600)
    assert p["monthly"] == 60
    assert p["progress_without_change"] == 0.21


def test_monthly_for_target_capped_by_margin():
    p = monthly_for_target(0, 100_000, 120, monthly_margin=100)
    assert p["monthly"] == 40 and p["capped"] is True
    assert monthly_for_target(0, 100_000, 120, monthly_margin=-50)["monthly"] == 0


def test_monthly_for_target_already_reached():
    p = monthly_for_target(50_000, 20_000, 12)
    assert p["monthly"] == 0 and p["progress_without_change"] == 1.0


def test_idle_cash_insight_check_values():
    s = make_snapshot(current_balance=54_400, savings_balance=0, liquid_balance=54_400, avg_monthly_spending=2_400)
    p = idle_cash_insight(s)
    assert (p["cushion"], p["idle_cash"], p["idle_ratio"]) == (14_400, 40_000, 0.74)


def test_idle_cash_insight_no_liquidity():
    p = idle_cash_insight(make_snapshot(liquid_balance=0, avg_monthly_spending=100))
    assert p["idle_cash"] == 0 and p["idle_ratio"] == 0


def test_emergency_buffer_goal():
    s = make_snapshot(savings_balance=1_800, avg_monthly_spending=1_600, monthly_income=2_450, monthly_margin=850)
    p = emergency_buffer_goal(s)
    assert p["target"] == 4_800 and p["gap"] == 3_000
    assert p["suggested_monthly"] == 250  # min(245, 340) rounded up to €10
    assert p["months_to_goal"] == 12


def test_loan_monthly_payment():
    p = loan_monthly_payment(25_000, 60)
    assert p["monthly_payment"] == pytest.approx(466.08, abs=0.01)
    assert p["total_cost"] == pytest.approx(466.08 * 60 - 25_000, abs=1)


def test_cashflow_forecast():
    s = make_snapshot(projected_balance_before_next_income=287.0, days_until_next_income=28)
    p = cashflow_forecast(s)
    assert p["projected_balance"] == 287.0 and p["days_until_next_income"] == 28


def test_run_calculator_loan_uses_latest_simulation():
    sims = [
        make_event("SIMULATION", {"simulation_type": "electric_car_loan", "amount": 30_000, "duration_months": 48}, days_ago=5),
        make_event("SIMULATION", {"simulation_type": "electric_car_loan", "amount": 20_000, "duration_months": 36}, days_ago=1),
        make_event("SIMULATION", {"simulation_type": "mortgage", "amount": 300_000, "duration_months": 240}),
    ]
    params = {"simulation_types": "electric_car_loan,car_loan", "default_amount": 25_000, "default_months": 60}
    p = run_calculator("loan_monthly_payment", make_snapshot(), params, sims)
    assert (p["amount"], p["duration_months"], p["from_simulation"]) == (20_000, 36, True)
    p = run_calculator("loan_monthly_payment", make_snapshot(), params, [])
    assert (p["amount"], p["duration_months"], p["from_simulation"]) == (25_000, 60, False)


def test_run_calculator_monthly_for_target_reads_snapshot():
    s = make_snapshot(savings_balance=2_400, monthly_margin=600)
    p = run_calculator("monthly_for_target", s, {"target": 20_000, "horizon_years": 18, "current_source": "savings_balance"})
    assert p["monthly"] == 60 and p["horizon_years"] == 18
