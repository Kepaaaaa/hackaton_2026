"""Moment rules (A.9). Owner: T3.

Confidence = min(1, Σ weight × strongest strength per signal type) within `ttl_days`.
If `requires_any` is set and none of those signals is present, the confidence is
capped at `cap_without_required` (sensitive moments must be declared, never inferred).
"""

from __future__ import annotations

from app.models.common import MomentType as M
from app.models.common import SignalType as S
from app.rules.schema import MomentRule

ACTIVE_THRESHOLD = 0.40
EMERGING_THRESHOLD = 0.20

MOMENT_RULES: list[MomentRule] = [
    MomentRule(
        moment=M.FIRST_SALARY,
        signal_weights={S.FIRST_RECURRING_SALARY: 0.70, S.SALARY_RECEIVED: 0.15, S.LOW_EMERGENCY_BUFFER: 0.10},
        ttl_days=90,
    ),
    MomentRule(
        moment=M.NEW_PARENT,
        signal_weights={
            S.PARENTHOOD_DECLARED: 0.55,
            S.CHILD_ACCOUNT_OPENED: 0.25,
            S.CHILD_RELATED_EXPENSE: 0.20,
            S.NEW_RECURRING_CHILD_EXPENSES: 0.15,
            S.CHILD_SAVINGS_PAGE_VIEW: 0.10,
        },
        ttl_days=180,
        requires_any=[S.PARENTHOOD_DECLARED, S.CHILD_ACCOUNT_OPENED],
        cap_without_required=0.35,
    ),
    MomentRule(
        moment=M.RETIREMENT_TRANSITION,
        signal_weights={
            S.RECURRING_PENSION_STARTED: 0.45,
            S.SALARY_STOPPED: 0.35,
            S.RETIREMENT_DECLARED: 0.30,
            S.RETIREMENT_PAGE_VIEW: 0.10,
            S.HIGH_IDLE_CASH: 0.10,
        },
        ttl_days=180,
    ),
    MomentRule(
        moment=M.TRAVEL,
        signal_weights={
            S.AIR_TRAVEL_ACTIVITY: 0.35,
            S.HOTEL_BOOKING: 0.25,
            S.TRAVEL_PAGE_VIEW: 0.20,
            S.FOREIGN_PAYMENT_SETTINGS_VIEWED: 0.20,
        },
        ttl_days=30,
    ),
    MomentRule(
        moment=M.CAR_PROJECT,
        signal_weights={
            S.AUTOMOTIVE_TRANSACTION: 0.25,
            S.ELECTRIC_CAR_LOAN_PAGE_VIEW: 0.30,
            S.ELECTRIC_CAR_LOAN_SIMULATION: 0.30,
            S.CAR_FINANCING_KBC_SEARCH: 0.15,
        },
        ttl_days=60,
    ),
    MomentRule(
        moment=M.HOME_BUYING,
        signal_weights={
            S.MORTGAGE_SIMULATION: 0.35,
            S.REPEATED_MORTGAGE_SIMULATION: 0.25,
            S.MORTGAGE_PAGE_VIEW: 0.25,
            S.HOME_KBC_SEARCH: 0.15,
        },
        ttl_days=90,
    ),
    MomentRule(
        moment=M.CASHFLOW_PRESSURE,
        signal_weights={S.LOW_PROJECTED_BALANCE: 0.55, S.LARGE_UNEXPECTED_EXPENSE: 0.35, S.LOW_EMERGENCY_BUFFER: 0.10},
        ttl_days=14,
    ),
    MomentRule(
        moment=M.LARGE_CASH_INFLOW,
        signal_weights={S.LARGE_CASH_INFLOW: 0.80, S.HIGH_IDLE_CASH: 0.20},
        ttl_days=60,
    ),
    MomentRule(
        moment=M.INVESTMENT_INTEREST,
        signal_weights={S.INVESTMENT_SIMULATION: 0.40, S.INVESTMENT_PAGE_VIEW: 0.30, S.INVESTMENT_KBC_SEARCH: 0.20},
        ttl_days=45,
    ),
]

# Human explanation recorded as `rule` evidence when `requires_any` caps a moment.
REQUIRED_SIGNAL_EXPLANATIONS: dict[M, str] = {
    M.NEW_PARENT: "Parenthood must be declared by the customer; spending alone is never enough",
}
