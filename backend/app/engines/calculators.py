"""Calculators (illustrative 3%/year, not KBC rates): monthly_for_target, idle_cash_insight,
emergency_buffer_goal, loan_monthly_payment, cashflow_forecast (A.9).

Owner: T4.

The five calculators are pure functions. `run_calculator` is the generic entry point used
by the experience builder: a journey action names a calculator and gives static `params`,
the adapter reads the rest from the snapshot (and, for loans, the latest simulation event).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from app.models.common import EventType
from app.models.event import CustomerEvent
from app.models.snapshot import FinancialSnapshot

Payload = dict[str, float | int | str | bool]

DEFAULT_SAVINGS_RATE = 0.03  # illustrative, not a KBC rate
DEFAULT_LOAN_RATE = 0.045  # illustrative, not a KBC rate
MARGIN_CAP_SHARE = 0.40  # a savings suggestion never exceeds 40% of the monthly margin
SPENDING_FLOOR = 1.0


def _ceil_to(value: float, step: int = 10) -> int:
    return int(math.ceil(round(value, 2) / step) * step)


def _floor_to(value: float, step: int = 10) -> int:
    return int(math.floor(round(value, 2) / step) * step)


def monthly_for_target(
    current: float,
    target: float,
    months: int,
    annual_rate: float = DEFAULT_SAVINGS_RATE,
    monthly_margin: float | None = None,
) -> Payload:
    """Monthly deposit to grow `current` into `target` in `months`, rounded up to the next €10.

    Capped at 40% of `monthly_margin` when given. `progress_without_change` is the share of
    the target reached by the current amount alone.
    """
    months = max(1, int(months))
    r = annual_rate / 12
    growth = (1 + r) ** months if r else 1.0
    annuity = (growth - 1) / r if r else float(months)
    future_current = current * growth
    needed = max(0.0, (target - future_current) / annuity)
    monthly = _ceil_to(needed) if needed > 0 else 0
    capped = False
    if monthly_margin is not None:
        cap = _floor_to(max(0.0, monthly_margin) * MARGIN_CAP_SHARE)
        if monthly > cap:
            monthly, capped = cap, True
    return {
        "monthly": monthly,
        "current": round(current, 2),
        "target": round(target, 2),
        "months": months,
        "annual_rate": annual_rate,
        "progress_without_change": round(min(1.0, future_current / target), 2) if target > 0 else 1.0,
        "capped": capped,
    }


def idle_cash_insight(snapshot: FinancialSnapshot, cushion_months: int = 6) -> Payload:
    cushion = cushion_months * snapshot.avg_monthly_spending
    idle = max(0.0, snapshot.liquid_balance - cushion)
    ratio = idle / snapshot.liquid_balance if snapshot.liquid_balance > 0 else 0.0
    return {
        "liquid_balance": round(snapshot.liquid_balance, 2),
        "cushion_months": cushion_months,
        "cushion": round(cushion, 2),
        "idle_cash": round(idle, 2),
        "idle_ratio": round(ratio, 2),
    }


def emergency_buffer_goal(snapshot: FinancialSnapshot, target_months: int = 3) -> Payload:
    """Target = 3 months of spending; suggested monthly = min(10% income, 40% margin), to €10."""
    target = target_months * snapshot.avg_monthly_spending
    current = snapshot.savings_balance
    gap = max(0.0, target - current)
    suggested = min(0.10 * snapshot.monthly_income, MARGIN_CAP_SHARE * max(0.0, snapshot.monthly_margin))
    suggested_monthly = _ceil_to(suggested) if suggested > 0 else 0
    months_to_goal = math.ceil(gap / suggested_monthly) if suggested_monthly and gap else 0
    return {
        "target_months": target_months,
        "target": round(target, 2),
        "current": round(current, 2),
        "gap": round(gap, 2),
        "suggested_monthly": suggested_monthly,
        "months_to_goal": months_to_goal,
    }


def loan_monthly_payment(amount: float, months: int, annual_rate: float = DEFAULT_LOAN_RATE) -> Payload:
    """Standard annuity, illustrative."""
    months = max(1, int(months))
    r = annual_rate / 12
    payment = amount * r / (1 - (1 + r) ** -months) if r else amount / months
    return {
        "amount": round(amount, 2),
        "duration_months": months,
        "annual_rate": annual_rate,
        "monthly_payment": round(payment, 2),
        "total_cost": round(payment * months - amount, 2),
    }


def cashflow_forecast(snapshot: FinancialSnapshot) -> Payload:
    return {
        "current_balance": round(snapshot.current_balance, 2),
        "projected_balance": round(snapshot.projected_balance_before_next_income, 2),
        "days_until_next_income": snapshot.days_until_next_income,
        "next_income_date": snapshot.next_income_date.isoformat() if snapshot.next_income_date else "",
        "avg_monthly_spending": round(snapshot.avg_monthly_spending, 2),
    }


# --- Generic adapters (action params + snapshot + events -> payload) ---------------------------


def _latest_simulation(events: Sequence[CustomerEvent], simulation_types: Sequence[str]) -> Any:
    sims = [
        e for e in events if e.type == EventType.SIMULATION and str(e.data.simulation_type) in simulation_types
    ]
    return max(sims, key=lambda e: e.timestamp).data if sims else None


def _run_monthly_for_target(snapshot: FinancialSnapshot, params: Mapping[str, Any], events: Sequence[CustomerEvent]) -> Payload:
    current = float(getattr(snapshot, str(params.get("current_source", "savings_balance"))))
    payload = monthly_for_target(
        current=current,
        target=float(params["target"]),
        months=int(params["horizon_years"]) * 12,
        annual_rate=float(params.get("annual_rate", DEFAULT_SAVINGS_RATE)),
        monthly_margin=snapshot.monthly_margin,
    )
    payload["horizon_years"] = int(params["horizon_years"])
    return payload


def _run_loan(snapshot: FinancialSnapshot, params: Mapping[str, Any], events: Sequence[CustomerEvent]) -> Payload:
    types = str(params.get("simulation_types", ""))  # comma-separated (action params are scalars)
    sim = _latest_simulation(events, [t.strip() for t in types.split(",") if t.strip()])
    amount = sim.amount if sim is not None and sim.amount else float(params.get("default_amount", 25_000))
    months = sim.duration_months if sim is not None and sim.duration_months else int(params.get("default_months", 60))
    payload = loan_monthly_payment(amount, months, float(params.get("annual_rate", DEFAULT_LOAN_RATE)))
    payload["from_simulation"] = sim is not None
    return payload


CALCULATORS: dict[str, Callable[[FinancialSnapshot, Mapping[str, Any], Sequence[CustomerEvent]], Payload]] = {
    "monthly_for_target": _run_monthly_for_target,
    "idle_cash_insight": lambda s, p, e: idle_cash_insight(s, int(p.get("cushion_months", 6))),
    "emergency_buffer_goal": lambda s, p, e: emergency_buffer_goal(s, int(p.get("target_months", 3))),
    "loan_monthly_payment": _run_loan,
    "cashflow_forecast": lambda s, p, e: cashflow_forecast(s),
}


def run_calculator(
    name: str,
    snapshot: FinancialSnapshot,
    params: Mapping[str, Any] | None = None,
    events: Sequence[CustomerEvent] = (),
) -> Payload:
    return CALCULATORS[name](snapshot, params or {}, events)
