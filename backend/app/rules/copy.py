"""English texts / templates for the experience (hero, notices, why, checks, disclaimer).

Owner: T4.

Pure data. The experience builder picks texts by moment / journey / product / signal type,
never by customer. Why-texts are built from signal types (never from raw search queries).
"""

from __future__ import annotations

from typing import Literal

from app.models.common import JourneyType, MomentType, ProductType, SignalType
from app.rules.schema import RuleModel

Tone = Literal["calm", "positive", "attention", "warning"]


class HeroCopy(RuleModel):
    title: str
    subtitle: str
    tone: Tone


class CheckThresholds(RuleModel):
    buffer_ok_months: float = 3.0
    cashflow_ok_abs: float = 500.0
    cashflow_ok_ratio: float = 0.3


class ExperienceCopy(RuleModel):
    hero_by_moment: dict[MomentType, HeroCopy]
    hero_by_journey: dict[JourneyType, HeroCopy]
    hero_calm: HeroCopy
    hero_wait: HeroCopy
    hero_no_consent: HeroCopy
    covered_notice_by_product: dict[ProductType, str]
    covered_notice_default: str
    warning_notice: str
    wait_notice: str
    no_consent_notice: str
    why_by_signal: dict[SignalType, str]
    why_calm: str
    checks: dict[str, str]
    check_thresholds: CheckThresholds = CheckThresholds()
    protection_products: list[ProductType] = []
    disclaimer: str


HERO_BY_MOMENT: dict[MomentType, HeroCopy] = {
    MomentType.FIRST_SALARY: HeroCopy(title="Your first salary just arrived",
                                      subtitle="Let's build your financial foundation", tone="positive"),
    MomentType.NEW_PARENT: HeroCopy(title="Congratulations on your growing family",
                                    subtitle="A few things that can help you prepare", tone="positive"),
    MomentType.RETIREMENT_TRANSITION: HeroCopy(title="Welcome to a new chapter",
                                               subtitle="Let's organise your income and savings for retirement",
                                               tone="positive"),
    MomentType.TRAVEL: HeroCopy(title="Getting ready for a trip?",
                                subtitle="Here's what's already sorted and what to check", tone="positive"),
    MomentType.CAR_PROJECT: HeroCopy(title="Planning a new car?",
                                     subtitle="See the cost clearly and what you already have", tone="attention"),
    MomentType.HOME_BUYING: HeroCopy(title="Thinking about buying a home?",
                                     subtitle="Understand what you can borrow before you decide", tone="attention"),
    MomentType.CASHFLOW_PRESSURE: HeroCopy(title="Heads-up on your balance",
                                           subtitle="Your balance may run low before your next income",
                                           tone="warning"),
    MomentType.LARGE_CASH_INFLOW: HeroCopy(title="A large amount just came in",
                                           subtitle="Take a moment to decide what it should do for you",
                                           tone="attention"),
    MomentType.INVESTMENT_INTEREST: HeroCopy(title="Curious about investing?",
                                             subtitle="Start with the basics, at your own pace", tone="attention"),
}

HERO_BY_JOURNEY: dict[JourneyType, HeroCopy] = {
    JourneyType.FINANCIAL_FOUNDATION: HERO_BY_MOMENT[MomentType.FIRST_SALARY],
    JourneyType.FAMILY_START: HERO_BY_MOMENT[MomentType.NEW_PARENT],
    JourneyType.RETIREMENT_TRANSITION: HERO_BY_MOMENT[MomentType.RETIREMENT_TRANSITION],
    JourneyType.TRAVEL_READY: HERO_BY_MOMENT[MomentType.TRAVEL],
    JourneyType.CAR_PROJECT: HERO_BY_MOMENT[MomentType.CAR_PROJECT],
    JourneyType.HOME_BUYING: HERO_BY_MOMENT[MomentType.HOME_BUYING],
    JourneyType.CASHFLOW_SUPPORT: HERO_BY_MOMENT[MomentType.CASHFLOW_PRESSURE],
    JourneyType.INVESTMENT_START: HERO_BY_MOMENT[MomentType.INVESTMENT_INTEREST],
}

WHY_BY_SIGNAL: dict[SignalType, str] = {
    SignalType.SALARY_RECEIVED: "A salary was paid into your account",
    SignalType.PENSION_RECEIVED: "A pension payment was received",
    SignalType.AIR_TRAVEL_ACTIVITY: "You paid for a flight",
    SignalType.HOTEL_BOOKING: "You paid for a hotel",
    SignalType.TRAVEL_PAGE_VIEW: "You looked at travel pages in the KBC app",
    SignalType.FOREIGN_PAYMENT_SETTINGS_VIEWED: "You checked your card settings for abroad",
    SignalType.AUTOMOTIVE_TRANSACTION: "You made a payment to a car dealer or garage",
    SignalType.ELECTRIC_CAR_LOAN_PAGE_VIEW: "You looked at the electric car loan page",
    SignalType.ELECTRIC_CAR_LOAN_SIMULATION: "You simulated a car loan",
    SignalType.CAR_FINANCING_KBC_SEARCH: "You searched KBC about car financing",
    SignalType.MORTGAGE_PAGE_VIEW: "You looked at mortgage pages",
    SignalType.MORTGAGE_SIMULATION: "You simulated a mortgage",
    SignalType.HOME_KBC_SEARCH: "You searched KBC about buying a home",
    SignalType.INVESTMENT_PAGE_VIEW: "You looked at investment pages",
    SignalType.INVESTMENT_SIMULATION: "You simulated an investment plan",
    SignalType.INVESTMENT_KBC_SEARCH: "You searched KBC about investing",
    SignalType.CHILD_SAVINGS_PAGE_VIEW: "You looked at child savings",
    SignalType.CHILD_ACCOUNT_OPENED: "You opened a child savings account",
    SignalType.CHILD_RELATED_EXPENSE: "Recent purchases for a baby",
    SignalType.PARENTHOOD_DECLARED: "You told us you are expecting a child",
    SignalType.RETIREMENT_DECLARED: "You told us you are retiring",
    SignalType.RETIREMENT_PAGE_VIEW: "You looked at retirement planning",
    SignalType.LARGE_UNEXPECTED_EXPENSE: "A large unexpected expense",
    SignalType.LARGE_CASH_INFLOW: "A large amount came into your account",
    SignalType.SAVINGS_TRANSFER: "You moved money to savings",
    SignalType.FIRST_RECURRING_SALARY: "Your first regular salary arrived",
    SignalType.SALARY_STOPPED: "Your salary payments stopped",
    SignalType.RECURRING_PENSION_STARTED: "Regular pension payments started",
    SignalType.NEW_RECURRING_CHILD_EXPENSES: "New regular child-related expenses",
    SignalType.REPEATED_MORTGAGE_SIMULATION: "You simulated a mortgage several times",
    SignalType.LOW_PROJECTED_BALANCE: "Your balance may run low before your next income",
    SignalType.LOW_EMERGENCY_BUFFER: "Your savings cover less than 3 months of expenses",
    SignalType.HIGH_IDLE_CASH: "A large part of your money is sitting idle",
}

COPY = ExperienceCopy(
    hero_by_moment=HERO_BY_MOMENT,
    hero_by_journey=HERO_BY_JOURNEY,
    hero_calm=HeroCopy(title="Everything looks on track.", subtitle="Nothing needs your attention today.", tone="calm"),
    hero_wait=HeroCopy(title="Everything looks on track.",
                       subtitle="Nothing needs your attention today. We'll keep an eye out for you.", tone="calm"),
    hero_no_consent=HeroCopy(title="Your KBC overview",
                             subtitle="Personalization is off. You see the standard view.", tone="calm"),
    covered_notice_by_product={
        ProductType.travel_insurance: "You're already covered for your trip.",
        ProductType.car_insurance: "Your car insurance is already in place.",
        ProductType.family_insurance: "Your family protection is already in place.",
        ProductType.child_savings_account: "You already have a child savings account.",
        ProductType.pension_savings: "You already save for your pension.",
        ProductType.investment_plan: "You already have an investment plan.",
    },
    covered_notice_default="You already have this product.",
    warning_notice="Your balance may run low before your next income. New offers are paused until it recovers.",
    wait_notice="Something may be changing. We'll wait until it's clearer before suggesting anything.",
    no_consent_notice="Personalization is turned off. You can turn it back on at any time.",
    why_by_signal=WHY_BY_SIGNAL,
    why_calm="No life moment currently needs your attention",
    checks={
        "buffer": "Safety cushion",
        "buffer_detail": "{months:.1f} months of expenses set aside",
        "cashflow": "Balance until next income",
        "cashflow_detail": "About €{projected:,.0f} expected before your next income",
        "coverage": "Protection",
        "coverage_detail_ok": "{count} protection product(s) in place, nothing missing for what's happening now",
        "coverage_detail_gap": "Something relevant is not covered yet",
        "moments": "Life moments",
        "moments_detail_none": "No life moment needs attention",
        "moments_detail_some": "Detected: {moments}",
        "feedback": "Your feedback",
        "feedback_detail_none": "No suggestion was dismissed",
        "feedback_detail_some": "We respect your choice on: {journeys}",
    },
    protection_products=[
        ProductType.home_insurance, ProductType.car_insurance, ProductType.travel_insurance,
        ProductType.family_insurance, ProductType.life_insurance,
    ],
    disclaimer="Amounts are illustrative simulations at 3% per year, not KBC rates or advice. Synthetic data.",
)
