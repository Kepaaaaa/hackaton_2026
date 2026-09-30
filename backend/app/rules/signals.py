"""Signal rules: EVENT_SIGNAL_RULES, PATTERN_THRESHOLDS, SIGNAL_TTL_DAYS (A.9). Owner: T2.

Event rules turn one event into at most one signal each. Description templates are
formatted by the signal engine with these placeholders: {amount}, {merchant},
{category}, {page}, {simulation_type}, {product}, {life_event}, {ago}. The raw
KBC search query is never available to templates.
"""

from __future__ import annotations

from app.models.common import EventType, SignalType
from app.rules.schema import DataMatch, PatternThresholds, SignalEventRule

_TX = EventType.TRANSACTION
_PAGE = EventType.PAGE_VIEW
_SIM = EventType.SIMULATION
_SEARCH = EventType.KBC_SEARCH


def _tx(category: str | list[str], direction: str, *extra: DataMatch) -> list[DataMatch]:
    op = "in" if isinstance(category, list) else "eq"
    return [DataMatch(field="category", op=op, value=category), DataMatch(field="direction", value=direction), *extra]


def _eq(field: str, value: str) -> list[DataMatch]:
    return [DataMatch(field=field, value=value)]


EVENT_SIGNAL_RULES: list[SignalEventRule] = [
    # Income
    SignalEventRule(
        event_type=_TX, match=_tx("salary", "in"), signal=SignalType.SALARY_RECEIVED, strength=1.0,
        description="Salary of {amount} from {merchant}, {ago}",
    ),
    SignalEventRule(
        event_type=_TX, match=_tx("pension", "in"), signal=SignalType.PENSION_RECEIVED, strength=1.0,
        description="Pension of {amount} from {merchant}, {ago}",
    ),
    SignalEventRule(
        event_type=_TX, match=_tx(["other_income", "refund"], "in", DataMatch(field="amount", op="ge", value=5000)),
        signal=SignalType.LARGE_CASH_INFLOW, strength=1.0,
        description="Large incoming payment of {amount} from {merchant}, {ago}",
    ),
    # Travel (a payment alone is ambiguous: could be a gift or a business trip)
    SignalEventRule(
        event_type=_TX, match=_tx("airline", "out"), signal=SignalType.AIR_TRAVEL_ACTIVITY, strength=0.8,
        description="Airline payment of {amount} at {merchant}, {ago}",
    ),
    SignalEventRule(
        event_type=_TX, match=_tx("hotel", "out"), signal=SignalType.HOTEL_BOOKING, strength=0.8,
        description="Hotel payment of {amount} at {merchant}, {ago}",
    ),
    SignalEventRule(
        event_type=_PAGE, match=_eq("page", "travel_insurance"), signal=SignalType.TRAVEL_PAGE_VIEW, strength=1.0,
        description="Viewed the KBC travel insurance page, {ago}",
    ),
    SignalEventRule(
        event_type=_PAGE, match=_eq("page", "card_abroad_settings"),
        signal=SignalType.FOREIGN_PAYMENT_SETTINGS_VIEWED, strength=1.0,
        description="Opened the card settings for payments abroad, {ago}",
    ),
    # Car
    SignalEventRule(
        event_type=_TX, match=_tx("automotive", "out"), signal=SignalType.AUTOMOTIVE_TRANSACTION, strength=1.0,
        description="Automotive payment of {amount} at {merchant}, {ago}",
    ),
    SignalEventRule(
        event_type=_PAGE, match=_eq("page", "electric_car_loan"),
        signal=SignalType.ELECTRIC_CAR_LOAN_PAGE_VIEW, strength=1.0,
        description="Viewed the KBC electric car loan page, {ago}",
    ),
    SignalEventRule(
        event_type=_SIM, match=_eq("simulation_type", "electric_car_loan"),
        signal=SignalType.ELECTRIC_CAR_LOAN_SIMULATION, strength=1.0,
        description="Ran an electric car loan simulation, {ago}",
    ),
    SignalEventRule(
        event_type=_SEARCH,
        keyword_groups=[["car", "vehicle", "ev", "electric"], ["loan", "financ", "borrow", "credit"]],
        signal=SignalType.CAR_FINANCING_KBC_SEARCH, strength=1.0,
        description="KBC search about car financing, {ago}",
    ),
    # Home
    SignalEventRule(
        event_type=_PAGE, match=_eq("page", "mortgage"), signal=SignalType.MORTGAGE_PAGE_VIEW, strength=1.0,
        description="Viewed the KBC mortgage page, {ago}",
    ),
    SignalEventRule(
        event_type=_SIM, match=_eq("simulation_type", "mortgage"), signal=SignalType.MORTGAGE_SIMULATION, strength=1.0,
        description="Ran a mortgage simulation, {ago}",
    ),
    SignalEventRule(
        event_type=_SEARCH, keyword_groups=[["mortgage", "home", "house", "apartment", "flat", "property"]],
        signal=SignalType.HOME_KBC_SEARCH, strength=1.0,
        description="KBC search about buying a home, {ago}",
    ),
    # Investment
    SignalEventRule(
        event_type=_PAGE, match=_eq("page", "investment_info"), signal=SignalType.INVESTMENT_PAGE_VIEW, strength=1.0,
        description="Viewed the KBC investment information page, {ago}",
    ),
    SignalEventRule(
        event_type=_SIM, match=_eq("simulation_type", "investment_plan"),
        signal=SignalType.INVESTMENT_SIMULATION, strength=1.0,
        description="Ran an investment plan simulation, {ago}",
    ),
    SignalEventRule(
        event_type=_SEARCH, keyword_groups=[["invest", "stock", "fund", "etf", "shares", "portfolio"]],
        signal=SignalType.INVESTMENT_KBC_SEARCH, strength=1.0,
        description="KBC search about investing, {ago}",
    ),
    # Family (parenthood is declared, spending alone stays a weak hint)
    SignalEventRule(
        event_type=_PAGE, match=_eq("page", "child_savings"), signal=SignalType.CHILD_SAVINGS_PAGE_VIEW, strength=1.0,
        description="Viewed the KBC child savings page, {ago}",
    ),
    SignalEventRule(
        event_type=EventType.PRODUCT_OPENED, match=_eq("product", "child_savings_account"),
        signal=SignalType.CHILD_ACCOUNT_OPENED, strength=1.0,
        description="Opened a child savings account, {ago}",
    ),
    SignalEventRule(
        event_type=_TX, match=_tx(["baby_supplies", "childcare"], "out"),
        signal=SignalType.CHILD_RELATED_EXPENSE, strength=0.6,
        description="Child-related payment of {amount} at {merchant}, {ago}",
    ),
    SignalEventRule(
        event_type=EventType.DECLARED_LIFE_EVENT, match=[DataMatch(field="life_event", op="in", value=["expecting_child", "child_born"])],
        signal=SignalType.PARENTHOOD_DECLARED, strength=1.0,
        description="Told KBC about a new child ({life_event}), {ago}",
    ),
    # Retirement
    SignalEventRule(
        event_type=EventType.DECLARED_LIFE_EVENT, match=_eq("life_event", "retiring"),
        signal=SignalType.RETIREMENT_DECLARED, strength=1.0,
        description="Told KBC about retiring, {ago}",
    ),
    SignalEventRule(
        event_type=_PAGE, match=_eq("page", "retirement_planning"), signal=SignalType.RETIREMENT_PAGE_VIEW, strength=1.0,
        description="Viewed the KBC retirement planning page, {ago}",
    ),
    # Cash flow
    SignalEventRule(
        event_type=_TX, match=_tx("unexpected_expense", "out", DataMatch(field="amount", op="ge", value=500)),
        signal=SignalType.LARGE_UNEXPECTED_EXPENSE, strength=1.0,
        description="Unexpected expense of {amount} at {merchant}, {ago}",
    ),
    SignalEventRule(
        event_type=_TX, match=_tx("savings_transfer", "out"), signal=SignalType.SAVINGS_TRANSFER, strength=1.0,
        description="Transfer of {amount} to savings, {ago}",
    ),
    # RECOMMENDATION_FEEDBACK and JOURNEY_INTERACTION produce no signal on purpose:
    # the decision engine reads feedback events directly.
]

PATTERN_THRESHOLDS = PatternThresholds()

DEFAULT_SIGNAL_TTL_DAYS = 60
SIGNAL_TTL_DAYS: dict[SignalType, int] = {
    # Declared or structural facts stay relevant longer
    SignalType.PARENTHOOD_DECLARED: 365,
    SignalType.RETIREMENT_DECLARED: 365,
    SignalType.CHILD_ACCOUNT_OPENED: 365,
    SignalType.FIRST_RECURRING_SALARY: 90,
    SignalType.SALARY_STOPPED: 180,
    SignalType.RECURRING_PENSION_STARTED: 180,
    SignalType.NEW_RECURRING_CHILD_EXPENSES: 180,
    # Short-lived behaviour
    SignalType.AIR_TRAVEL_ACTIVITY: 30,
    SignalType.HOTEL_BOOKING: 30,
    SignalType.TRAVEL_PAGE_VIEW: 30,
    SignalType.FOREIGN_PAYMENT_SETTINGS_VIEWED: 30,
    SignalType.LARGE_UNEXPECTED_EXPENSE: 30,
    # Snapshot-based: recomputed on every read, the TTL is informative only
    SignalType.LOW_PROJECTED_BALANCE: 14,
    SignalType.LOW_EMERGENCY_BUFFER: 30,
    SignalType.HIGH_IDLE_CASH: 30,
}
