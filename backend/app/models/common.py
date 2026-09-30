"""Shared vocabulary (frozen enums, A.6) and base types. Owner: T0.

Enums may only be extended (new members), never renamed or shrunk.
"""

from __future__ import annotations

import unicodedata
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

CustomerId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{1,31}$")]


class StrictModel(BaseModel):
    """Base for every model: unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")


def reject_control_chars(value: str) -> str:
    """Raise if the string contains control characters (used by field validators)."""
    if any(unicodedata.category(ch) in ("Cc", "Cf") for ch in value):
        raise ValueError("control characters are not allowed")
    return value


def round_money(value: float) -> float:
    return round(float(value), 2)


class EventType(StrEnum):
    TRANSACTION = "TRANSACTION"
    PAGE_VIEW = "PAGE_VIEW"
    SIMULATION = "SIMULATION"
    KBC_SEARCH = "KBC_SEARCH"
    PRODUCT_OPENED = "PRODUCT_OPENED"
    DECLARED_LIFE_EVENT = "DECLARED_LIFE_EVENT"
    RECOMMENDATION_FEEDBACK = "RECOMMENDATION_FEEDBACK"
    JOURNEY_INTERACTION = "JOURNEY_INTERACTION"


class TransactionCategory(StrEnum):
    salary = "salary"
    pension = "pension"
    other_income = "other_income"
    refund = "refund"
    rent = "rent"
    mortgage_payment = "mortgage_payment"
    loan_repayment = "loan_repayment"
    groceries = "groceries"
    utilities = "utilities"
    transport = "transport"
    leisure = "leisure"
    restaurants = "restaurants"
    airline = "airline"
    hotel = "hotel"
    automotive = "automotive"
    childcare = "childcare"
    baby_supplies = "baby_supplies"
    insurance_premium = "insurance_premium"
    savings_transfer = "savings_transfer"
    investment = "investment"
    unexpected_expense = "unexpected_expense"
    other = "other"


class KbcPage(StrEnum):
    electric_car_loan = "electric_car_loan"
    car_loan = "car_loan"
    car_insurance = "car_insurance"
    mortgage = "mortgage"
    home_insurance = "home_insurance"
    travel_insurance = "travel_insurance"
    card_abroad_settings = "card_abroad_settings"
    investment_info = "investment_info"
    pension_savings = "pension_savings"
    child_savings = "child_savings"
    family_insurance = "family_insurance"
    budgeting_tools = "budgeting_tools"
    retirement_planning = "retirement_planning"
    savings_accounts = "savings_accounts"


class SimulationType(StrEnum):
    electric_car_loan = "electric_car_loan"
    car_loan = "car_loan"
    mortgage = "mortgage"
    pension_savings = "pension_savings"
    investment_plan = "investment_plan"
    savings_plan = "savings_plan"


class ProductType(StrEnum):
    current_account = "current_account"
    savings_account = "savings_account"
    child_savings_account = "child_savings_account"
    pension_savings = "pension_savings"
    investment_plan = "investment_plan"
    mortgage = "mortgage"
    car_loan = "car_loan"
    consumer_loan = "consumer_loan"
    credit_card = "credit_card"
    debit_card = "debit_card"
    home_insurance = "home_insurance"
    car_insurance = "car_insurance"
    travel_insurance = "travel_insurance"
    family_insurance = "family_insurance"
    life_insurance = "life_insurance"


class LifeEventDeclared(StrEnum):
    expecting_child = "expecting_child"
    child_born = "child_born"
    retiring = "retiring"
    moving = "moving"
    new_job = "new_job"


class FeedbackType(StrEnum):
    NOT_RELEVANT = "NOT_RELEVANT"
    LATER = "LATER"
    USEFUL = "USEFUL"


class SignalType(StrEnum):
    # From single events
    SALARY_RECEIVED = "SALARY_RECEIVED"
    PENSION_RECEIVED = "PENSION_RECEIVED"
    AIR_TRAVEL_ACTIVITY = "AIR_TRAVEL_ACTIVITY"
    HOTEL_BOOKING = "HOTEL_BOOKING"
    TRAVEL_PAGE_VIEW = "TRAVEL_PAGE_VIEW"
    FOREIGN_PAYMENT_SETTINGS_VIEWED = "FOREIGN_PAYMENT_SETTINGS_VIEWED"
    AUTOMOTIVE_TRANSACTION = "AUTOMOTIVE_TRANSACTION"
    ELECTRIC_CAR_LOAN_PAGE_VIEW = "ELECTRIC_CAR_LOAN_PAGE_VIEW"
    ELECTRIC_CAR_LOAN_SIMULATION = "ELECTRIC_CAR_LOAN_SIMULATION"
    CAR_FINANCING_KBC_SEARCH = "CAR_FINANCING_KBC_SEARCH"
    MORTGAGE_PAGE_VIEW = "MORTGAGE_PAGE_VIEW"
    MORTGAGE_SIMULATION = "MORTGAGE_SIMULATION"
    HOME_KBC_SEARCH = "HOME_KBC_SEARCH"
    INVESTMENT_PAGE_VIEW = "INVESTMENT_PAGE_VIEW"
    INVESTMENT_SIMULATION = "INVESTMENT_SIMULATION"
    INVESTMENT_KBC_SEARCH = "INVESTMENT_KBC_SEARCH"
    CHILD_SAVINGS_PAGE_VIEW = "CHILD_SAVINGS_PAGE_VIEW"
    CHILD_ACCOUNT_OPENED = "CHILD_ACCOUNT_OPENED"
    CHILD_RELATED_EXPENSE = "CHILD_RELATED_EXPENSE"
    PARENTHOOD_DECLARED = "PARENTHOOD_DECLARED"
    RETIREMENT_DECLARED = "RETIREMENT_DECLARED"
    RETIREMENT_PAGE_VIEW = "RETIREMENT_PAGE_VIEW"
    LARGE_UNEXPECTED_EXPENSE = "LARGE_UNEXPECTED_EXPENSE"
    LARGE_CASH_INFLOW = "LARGE_CASH_INFLOW"
    SAVINGS_TRANSFER = "SAVINGS_TRANSFER"
    # From patterns over history + snapshot
    FIRST_RECURRING_SALARY = "FIRST_RECURRING_SALARY"
    SALARY_STOPPED = "SALARY_STOPPED"
    RECURRING_PENSION_STARTED = "RECURRING_PENSION_STARTED"
    NEW_RECURRING_CHILD_EXPENSES = "NEW_RECURRING_CHILD_EXPENSES"
    REPEATED_MORTGAGE_SIMULATION = "REPEATED_MORTGAGE_SIMULATION"
    LOW_PROJECTED_BALANCE = "LOW_PROJECTED_BALANCE"
    LOW_EMERGENCY_BUFFER = "LOW_EMERGENCY_BUFFER"
    HIGH_IDLE_CASH = "HIGH_IDLE_CASH"


class MomentType(StrEnum):
    FIRST_SALARY = "FIRST_SALARY"
    NEW_PARENT = "NEW_PARENT"
    RETIREMENT_TRANSITION = "RETIREMENT_TRANSITION"
    TRAVEL = "TRAVEL"
    CAR_PROJECT = "CAR_PROJECT"
    HOME_BUYING = "HOME_BUYING"
    CASHFLOW_PRESSURE = "CASHFLOW_PRESSURE"
    LARGE_CASH_INFLOW = "LARGE_CASH_INFLOW"
    INVESTMENT_INTEREST = "INVESTMENT_INTEREST"


class IntentType(StrEnum):
    BUILD_FINANCIAL_SAFETY = "BUILD_FINANCIAL_SAFETY"
    START_SAVING = "START_SAVING"
    LEARN_BUDGETING = "LEARN_BUDGETING"
    START_INVESTING = "START_INVESTING"
    CHILD_SAVING = "CHILD_SAVING"
    HOUSEHOLD_BUDGET_ADAPTATION = "HOUSEHOLD_BUDGET_ADAPTATION"
    FAMILY_PROTECTION = "FAMILY_PROTECTION"
    INCOME_REORGANIZATION = "INCOME_REORGANIZATION"
    SAVINGS_MANAGEMENT = "SAVINGS_MANAGEMENT"
    LONG_TERM_FINANCIAL_PLANNING = "LONG_TERM_FINANCIAL_PLANNING"
    PREPARE_TRIP = "PREPARE_TRIP"
    FINANCE_CAR = "FINANCE_CAR"
    PROTECT_CAR = "PROTECT_CAR"
    BUY_HOME = "BUY_HOME"
    STABILIZE_CASHFLOW = "STABILIZE_CASHFLOW"


class JourneyType(StrEnum):
    FINANCIAL_FOUNDATION = "FINANCIAL_FOUNDATION"
    FAMILY_START = "FAMILY_START"
    RETIREMENT_TRANSITION = "RETIREMENT_TRANSITION"
    TRAVEL_READY = "TRAVEL_READY"
    CAR_PROJECT = "CAR_PROJECT"
    HOME_BUYING = "HOME_BUYING"
    CASHFLOW_SUPPORT = "CASHFLOW_SUPPORT"
    INVESTMENT_START = "INVESTMENT_START"


class JourneyKind(StrEnum):
    SUPPORT = "SUPPORT"
    GUIDANCE = "GUIDANCE"
    COMMERCIAL = "COMMERCIAL"


class DecisionType(StrEnum):
    SHOW_JOURNEY = "SHOW_JOURNEY"
    SHOW_GUIDANCE = "SHOW_GUIDANCE"
    SHOW_PRODUCT = "SHOW_PRODUCT"
    SHOW_SERVICE = "SHOW_SERVICE"
    SHOW_WARNING = "SHOW_WARNING"
    PASSIVE_PERSONALIZATION = "PASSIVE_PERSONALIZATION"
    WAIT = "WAIT"
    NO_ACTION = "NO_ACTION"


class DecisionLevel(StrEnum):
    PROACTIVE = "PROACTIVE"
    SUGGESTION = "SUGGESTION"
    PASSIVE = "PASSIVE"
    NONE = "NONE"


class ActionKind(StrEnum):
    INFO = "INFO"
    SIMULATION = "SIMULATION"
    PRODUCT = "PRODUCT"
    SERVICE = "SERVICE"
    APPOINTMENT = "APPOINTMENT"
    SETTINGS = "SETTINGS"
    EDUCATION = "EDUCATION"


class ActionStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    ALREADY_COVERED = "ALREADY_COVERED"
    HIDDEN = "HIDDEN"


class MomentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EMERGING = "EMERGING"


class Evidence(StrictModel):
    kind: Literal["signal", "moment", "profile", "product", "feedback", "financial", "rule"]
    ref: str
    contribution: float
    detail: str
    source_event_ids: list[str] = []
