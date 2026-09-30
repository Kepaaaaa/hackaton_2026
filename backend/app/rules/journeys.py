"""Journey catalog: JOURNEYS (A.9, T4 deliverable 1).

Owner: T4.

A journey is a reusable set of actions. `serves_intents` says how relevant the journey is
for each intent (0..1); every IntentType is served by at least one journey. Actions with a
`product` are marked ALREADY_COVERED when the customer owns it. `calculator` + `params`
feed the action payload (see engines/calculators.py).
"""

from __future__ import annotations

from app.models.common import ActionKind as K
from app.models.common import IntentType as I
from app.models.common import JourneyKind, JourneyType, ProductType
from app.models.journey import JourneyActionDef as A
from app.models.journey import JourneyDef
from app.rules.schema import Condition

_HAS_INCOME = Condition(field="monthly_income", op="gt", value=0)

_JOURNEY_LIST: list[JourneyDef] = [
    JourneyDef(
        type=JourneyType.FINANCIAL_FOUNDATION,
        title="Build your financial foundation",
        kind=JourneyKind.GUIDANCE,
        serves_intents={I.BUILD_FINANCIAL_SAFETY: 1.0, I.START_SAVING: 0.9, I.LEARN_BUDGETING: 0.8},
        usefulness=0.85,
        actions=[
            A(id="EMERGENCY_BUFFER_GOAL", kind=K.INFO, label="Set your safety cushion goal",
              calculator="emergency_buffer_goal", params={"target_months": 3}),
            # No `product`: it sets up a monthly transfer, so it is never marked covered.
            A(id="START_SAVINGS_PLAN", kind=K.PRODUCT, label="Start a monthly savings transfer",
              calculator="emergency_buffer_goal", params={"target_months": 3}),
            A(id="BUDGET_OVERVIEW", kind=K.SERVICE, label="See where your money goes"),
            A(id="LONG_TERM_PENSION_SAVINGS", kind=K.PRODUCT, label="Think long term: pension savings",
              product=ProductType.pension_savings, calculator="monthly_for_target",
              params={"target": 100_000, "horizon_years": 40, "current_source": "savings_balance"}),
            A(id="LEARN_THE_BASICS", kind=K.EDUCATION, label="Money basics in 5 minutes"),
        ],
    ),
    JourneyDef(
        type=JourneyType.FAMILY_START,
        title="Prepare for your growing family",
        kind=JourneyKind.GUIDANCE,
        serves_intents={I.CHILD_SAVING: 1.0, I.HOUSEHOLD_BUDGET_ADAPTATION: 0.9, I.FAMILY_PROTECTION: 0.9},
        usefulness=0.9,
        actions=[
            A(id="CHILD_LONG_TERM_SAVINGS", kind=K.PRODUCT, label="Save for your child's future",
              product=ProductType.child_savings_account, calculator="monthly_for_target",
              params={"target": 20_000, "horizon_years": 18, "current_source": "savings_balance"}),
            A(id="FAMILY_BUDGET_REVIEW", kind=K.SERVICE, label="Review your family budget"),
            A(id="FAMILY_PROTECTION_CHECK", kind=K.PRODUCT, label="Check your family protection",
              product=ProductType.family_insurance),
            A(id="PARENTAL_BENEFITS_INFO", kind=K.EDUCATION, label="Parental leave and child benefits"),
        ],
    ),
    JourneyDef(
        type=JourneyType.RETIREMENT_TRANSITION,
        title="Settle into retirement",
        kind=JourneyKind.GUIDANCE,
        serves_intents={
            I.INCOME_REORGANIZATION: 1.0,
            I.SAVINGS_MANAGEMENT: 0.9,
            I.LONG_TERM_FINANCIAL_PLANNING: 0.9,
        },
        usefulness=0.9,
        actions=[
            A(id="INCOME_OVERVIEW", kind=K.INFO, label="Your new monthly income"),
            A(id="IDLE_CASH_INSIGHT", kind=K.INFO, label="Money sitting idle on your current account",
              calculator="idle_cash_insight", params={"cushion_months": 6}),
            A(id="PREPARE_ADVISOR_APPOINTMENT", kind=K.APPOINTMENT, label="Prepare an advisor appointment"),
            A(id="PLANNING_BASICS", kind=K.EDUCATION, label="Planning basics for retirement"),
        ],
    ),
    JourneyDef(
        type=JourneyType.TRAVEL_READY,
        title="Get ready for your trip",
        kind=JourneyKind.GUIDANCE,
        serves_intents={I.PREPARE_TRIP: 1.0},
        usefulness=0.8,
        actions=[
            A(id="CARD_ABROAD_CHECK", kind=K.SETTINGS, label="Check your card settings abroad"),
            A(id="TRAVEL_COVERAGE_STATUS", kind=K.INFO, label="Your travel coverage"),
            A(id="TRAVEL_INSURANCE", kind=K.PRODUCT, label="Travel insurance", product=ProductType.travel_insurance),
            A(id="TRAVEL_BUDGET", kind=K.SERVICE, label="Set a travel budget"),
            A(id="FOREIGN_PAYMENT_GUIDE", kind=K.EDUCATION, label="Paying abroad: what to know"),
        ],
    ),
    JourneyDef(
        type=JourneyType.CAR_PROJECT,
        title="Your car project",
        kind=JourneyKind.GUIDANCE,
        serves_intents={I.FINANCE_CAR: 1.0, I.PROTECT_CAR: 0.6},
        usefulness=0.85,
        eligibility=[_HAS_INCOME],
        actions=[
            A(id="CAR_FINANCING_INFO", kind=K.EDUCATION, label="How car financing works"),
            A(id="CAR_LOAN_SIMULATION", kind=K.SIMULATION, label="Simulate your car loan",
              calculator="loan_monthly_payment",
              params={"simulation_types": "electric_car_loan,car_loan", "default_amount": 25_000, "default_months": 60}),
            A(id="CAR_INSURANCE_STATUS", kind=K.PRODUCT, label="Car insurance", product=ProductType.car_insurance),
            A(id="BUDGET_IMPACT", kind=K.INFO, label="Impact on your monthly budget"),
            A(id="SAVINGS_IMPACT", kind=K.INFO, label="Impact on your savings"),
        ],
    ),
    JourneyDef(
        type=JourneyType.HOME_BUYING,
        title="Buying a home",
        kind=JourneyKind.COMMERCIAL,
        serves_intents={I.BUY_HOME: 1.0},
        usefulness=0.8,
        eligibility=[_HAS_INCOME],
        actions=[
            A(id="MORTGAGE_SIMULATION", kind=K.SIMULATION, label="Simulate your mortgage",
              calculator="loan_monthly_payment",
              params={"simulation_types": "mortgage", "default_amount": 250_000, "default_months": 300,
                      "annual_rate": 0.035}),
            A(id="BORROWING_CAPACITY", kind=K.INFO, label="How much could you borrow?"),
            A(id="DEPOSIT_SAVINGS", kind=K.SERVICE, label="Save for your deposit"),
            A(id="ADVISOR_APPOINTMENT", kind=K.APPOINTMENT, label="Talk to a mortgage advisor"),
        ],
    ),
    JourneyDef(
        type=JourneyType.CASHFLOW_SUPPORT,
        title="Keep your balance on track",
        kind=JourneyKind.SUPPORT,
        urgent=True,
        serves_intents={I.STABILIZE_CASHFLOW: 1.0},
        usefulness=1.0,
        actions=[
            A(id="CASHFLOW_FORECAST", kind=K.INFO, label="Your balance until next income",
              calculator="cashflow_forecast"),
            A(id="UPCOMING_PAYMENTS", kind=K.SERVICE, label="Upcoming payments"),
            A(id="SPENDING_PAUSE_TIPS", kind=K.EDUCATION, label="Ways to ease the next weeks"),
            A(id="TALK_TO_ADVISOR", kind=K.APPOINTMENT, label="Talk to an advisor"),
        ],
    ),
    JourneyDef(
        type=JourneyType.INVESTMENT_START,
        title="Start investing",
        kind=JourneyKind.COMMERCIAL,
        serves_intents={I.START_INVESTING: 1.0},
        usefulness=0.8,
        eligibility=[Condition(field="emergency_buffer_months", op="ge", value=1)],
        actions=[
            A(id="INVESTMENT_BASICS", kind=K.EDUCATION, label="Investing basics"),
            A(id="INVESTMENT_PLAN_SIMULATION", kind=K.SIMULATION, label="Simulate a monthly investment plan"),
            A(id="RISK_PROFILE", kind=K.SERVICE, label="Discover your risk profile"),
            A(id="INVESTMENT_PLAN", kind=K.PRODUCT, label="Investment plan", product=ProductType.investment_plan),
        ],
    ),
]

JOURNEYS: dict[JourneyType, JourneyDef] = {j.type: j for j in _JOURNEY_LIST}
