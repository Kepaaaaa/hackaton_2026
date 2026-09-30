"""compute_snapshot(customer, events, now) -> FinancialSnapshot (A.9). Owner: T2.

Pure function of the customer's seed balances, the event log and `now`.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from app.models.common import EventType, TransactionCategory
from app.models.customer import Customer
from app.models.event import CustomerEvent, TransactionEvent
from app.models.snapshot import FinancialSnapshot

INCOME_WINDOW_DAYS = 30
SPENDING_WINDOW_DAYS = 90
SPENDING_WINDOW_MONTHS = 3
DEBT_WINDOW_DAYS = 30
INCOME_PERIOD_DAYS = 30
CUSHION_MONTHS = 6
SPENDING_FLOOR = 1.0  # avoids division by zero in ratios

INCOME_CATEGORIES = {TransactionCategory.salary: "salary", TransactionCategory.pension: "pension"}
NON_SPENDING_CATEGORIES = {
    TransactionCategory.savings_transfer,
    TransactionCategory.investment,
    TransactionCategory.unexpected_expense,
}
DEBT_CATEGORIES = {TransactionCategory.mortgage_payment, TransactionCategory.loan_repayment}


def _transactions(events: Sequence[CustomerEvent], now: datetime) -> list[TransactionEvent]:
    return [e for e in events if e.type == EventType.TRANSACTION and e.timestamp <= now]


def _within(tx: TransactionEvent, now: datetime, days: int) -> bool:
    return tx.timestamp > now - timedelta(days=days)


def _money(value: float) -> float:
    return round(value, 2)


def _ratio(value: float) -> float:
    return round(value, 4)


def compute_snapshot(customer: Customer, events: Sequence[CustomerEvent], now: datetime) -> FinancialSnapshot:
    txs = _transactions(events, now)

    live_delta = sum(tx.data.signed_amount() for tx in txs if tx.origin == "live")
    current = sum(a.balance for a in customer.accounts if a.type == "current") + live_delta
    savings = sum(a.balance for a in customer.accounts if a.type == "savings")
    liquid = current + savings

    incomes = [tx for tx in txs if tx.data.direction == "in" and tx.data.category in INCOME_CATEGORIES]
    recent_incomes = [tx for tx in incomes if _within(tx, now, INCOME_WINDOW_DAYS)]
    monthly_income = sum(tx.data.amount for tx in recent_incomes)
    income_sources = sorted({INCOME_CATEGORIES[tx.data.category] for tx in recent_incomes})

    spending_total = sum(
        tx.data.amount
        for tx in txs
        if tx.data.direction == "out"
        and tx.data.category not in NON_SPENDING_CATEGORIES
        and _within(tx, now, SPENDING_WINDOW_DAYS)
    )
    avg_spending = spending_total / SPENDING_WINDOW_MONTHS
    spending_floor = max(avg_spending, SPENDING_FLOOR)

    # Without any known income, assume a full period until the next one.
    if incomes:
        next_income_date = (max(tx.timestamp for tx in incomes) + timedelta(days=INCOME_PERIOD_DAYS)).date()
        days_until = min(max((next_income_date - now.date()).days, 0), INCOME_PERIOD_DAYS)
    else:
        next_income_date = None
        days_until = INCOME_PERIOD_DAYS
    projected = current - avg_spending * days_until / INCOME_PERIOD_DAYS

    buffer_months = (savings + max(0.0, current - avg_spending)) / spending_floor
    idle_cash = max(0.0, liquid - CUSHION_MONTHS * avg_spending)
    idle_ratio = idle_cash / liquid if liquid > 0 else 0.0

    debt = sum(
        tx.data.amount
        for tx in txs
        if tx.data.direction == "out" and tx.data.category in DEBT_CATEGORIES and _within(tx, now, DEBT_WINDOW_DAYS)
    )
    debt_ratio = debt / monthly_income if monthly_income > 0 else 0.0

    return FinancialSnapshot(
        as_of=now,
        current_balance=_money(current),
        savings_balance=_money(savings),
        liquid_balance=_money(liquid),
        monthly_income=_money(monthly_income),
        income_sources=income_sources,
        avg_monthly_spending=_money(avg_spending),
        next_income_date=next_income_date,
        days_until_next_income=days_until,
        projected_balance_before_next_income=_money(projected),
        emergency_buffer_months=_ratio(buffer_months),
        idle_cash=_money(idle_cash),
        idle_ratio=_ratio(idle_ratio),
        monthly_debt_payments=_money(debt),
        debt_ratio=_ratio(debt_ratio),
        monthly_margin=_money(monthly_income - avg_spending),
    )
