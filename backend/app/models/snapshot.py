"""Financial snapshot computed from balances and the event log (A.7, formulas in A.9). Owner: T0."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import AwareDatetime

from app.models.common import StrictModel


class FinancialSnapshot(StrictModel):
    as_of: AwareDatetime
    current_balance: float
    savings_balance: float
    liquid_balance: float
    monthly_income: float
    income_sources: list[Literal["salary", "pension", "other"]]
    avg_monthly_spending: float
    next_income_date: date | None
    days_until_next_income: int
    projected_balance_before_next_income: float
    emergency_buffer_months: float
    idle_cash: float
    idle_ratio: float
    monthly_debt_payments: float
    debt_ratio: float
    monthly_margin: float  # monthly_income - avg_monthly_spending
