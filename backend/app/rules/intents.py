"""Intent rules (A.9). Owner: T3.

Confidence = clamp(Σ weight × ACTIVE moment confidence + Σ weight × signal strength
+ profile adjustments, 0, 1). Profile adjustments only nudge an intent that already has
a moment or signal behind it; they never create one on their own. `age` is never a path.
"""

from __future__ import annotations

from app.models.common import IntentType as I
from app.models.common import MomentType as M
from app.models.common import SignalType as S
from app.rules.schema import IntentRule, ProfileAdjustment

INTENT_MIN_CONFIDENCE = 0.10

_BEGINNER = "financial_profile.financial_maturity"

INTENT_RULES: list[IntentRule] = [
    IntentRule(
        intent=I.BUILD_FINANCIAL_SAFETY,
        moment_weights={M.FIRST_SALARY: 0.75, M.CASHFLOW_PRESSURE: 0.40},
        signal_weights={S.LOW_EMERGENCY_BUFFER: 0.25},
    ),
    IntentRule(
        intent=I.START_SAVING,
        moment_weights={M.FIRST_SALARY: 0.70, M.NEW_PARENT: 0.20},
        signal_weights={S.LOW_EMERGENCY_BUFFER: 0.15},
    ),
    IntentRule(
        intent=I.LEARN_BUDGETING,
        moment_weights={M.FIRST_SALARY: 0.50, M.NEW_PARENT: 0.20},
        profile_adjustments=[ProfileAdjustment(path=_BEGINNER, equals="beginner", delta=0.10)],
    ),
    IntentRule(
        intent=I.START_INVESTING,
        moment_weights={M.INVESTMENT_INTEREST: 0.80, M.FIRST_SALARY: 0.20, M.LARGE_CASH_INFLOW: 0.40},
        profile_adjustments=[ProfileAdjustment(path=_BEGINNER, equals="beginner", delta=-0.05)],
    ),
    IntentRule(
        intent=I.CHILD_SAVING,
        moment_weights={M.NEW_PARENT: 0.85},
        signal_weights={S.CHILD_SAVINGS_PAGE_VIEW: 0.10},
    ),
    IntentRule(intent=I.HOUSEHOLD_BUDGET_ADAPTATION, moment_weights={M.NEW_PARENT: 0.75}),
    IntentRule(intent=I.FAMILY_PROTECTION, moment_weights={M.NEW_PARENT: 0.70}),
    IntentRule(intent=I.INCOME_REORGANIZATION, moment_weights={M.RETIREMENT_TRANSITION: 0.85}),
    IntentRule(
        intent=I.SAVINGS_MANAGEMENT,
        moment_weights={M.RETIREMENT_TRANSITION: 0.70, M.LARGE_CASH_INFLOW: 0.50},
        signal_weights={S.HIGH_IDLE_CASH: 0.25},
    ),
    IntentRule(intent=I.LONG_TERM_FINANCIAL_PLANNING, moment_weights={M.RETIREMENT_TRANSITION: 0.70}),
    IntentRule(intent=I.PREPARE_TRIP, moment_weights={M.TRAVEL: 0.90}),
    IntentRule(
        intent=I.FINANCE_CAR,
        moment_weights={M.CAR_PROJECT: 0.80},
        signal_weights={S.ELECTRIC_CAR_LOAN_SIMULATION: 0.15},
    ),
    IntentRule(intent=I.PROTECT_CAR, moment_weights={M.CAR_PROJECT: 0.40}),
    IntentRule(intent=I.BUY_HOME, moment_weights={M.HOME_BUYING: 0.90}),
    IntentRule(intent=I.STABILIZE_CASHFLOW, moment_weights={M.CASHFLOW_PRESSURE: 0.95}),
]
