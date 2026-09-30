"""What the model looks at: signals (explainable rules) and the life events they point to.

The rules encode banking knowledge and say WHERE to look ("a large payment to a notary").
They never say HOW MUCH it counts: each (event, signal) pair starts with an expert prior
weight, and training replaces it with a weight learned from the bank's own outcomes.

Adding a case means adding a Signal and listing it under an Event. No code change.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .contract import CATEGORIES, FORBIDDEN_CATEGORIES, STEPS


@dataclass(frozen=True)
class Rule:
    kind: str                    # count | onset | stopped | spike | new_payer | abroad | web | declared
    categories: frozenset = frozenset()
    direction: str = "out"       # out = money leaves the account, in = money arrives
    window: int = 90             # days looked at, counted back from the as-of date
    baseline: int = 0            # days before the window, for onset / stopped / spike / new_payer
    min_count: int = 1
    min_amount: float = 0.0      # per transaction, absolute value
    min_total: float = 0.0
    factor: float = 0.0          # spike: recent daily spend >= factor x baseline daily spend
    topics: frozenset = frozenset()
    steps: frozenset = frozenset()   # web: only these steps (empty = any step)


@dataclass(frozen=True)
class Signal:
    id: str
    label: str          # customer-facing reason, shown in "Why this goal?"
    source: str         # transactions | search | declared
    rule: Rule


@dataclass(frozen=True)
class Event:
    id: str
    label: str
    sensitive: bool                 # never proposed on inference alone, see report.status
    products: tuple
    priors: dict = field(hash=False)  # signal id -> expert weight, used until trained
    # A labelled event counts as "current" at an as-of date when event_date falls in
    # [as_of - before, as_of + after]. Example: a birth up to 196 days ahead = pregnant.
    label_window: tuple = (90, 30)
    # How long a declaration stays true. Default: as long as the event itself stays current.
    declared_valid_days: int | None = None

    @property
    def declaration_days(self) -> int:
        return self.declared_valid_days or self.label_window[0] + 30


def _cats(*names):
    return frozenset(names)


def count(cats, window, min_count=1, min_amount=0.0, direction="out"):
    return Rule("count", _cats(*cats), direction, window, min_count=min_count, min_amount=min_amount)


def onset(cats, window, baseline, direction="out", min_count=1):
    return Rule("onset", _cats(*cats), direction, window, baseline, min_count=min_count)


def stopped(cats, window, baseline, direction="out", min_count=3):
    return Rule("stopped", _cats(*cats), direction, window, baseline, min_count=min_count)


def spike(cats, window, baseline, factor, min_total):
    return Rule("spike", _cats(*cats), "out", window, baseline, factor=factor, min_total=min_total)


def web(topics, window, steps=(), min_count=1):
    return Rule("web", window=window, topics=frozenset(topics), steps=frozenset(steps), min_count=min_count)


def declared():
    return Rule("declared")      # the window is the event's own declaration_days


SIMULATING = ("tool", "simulator", "form")

SIGNALS = {s.id: s for s in [
    # --- family ---------------------------------------------------------------------------------
    Signal("baby_purchases", "Several purchases in baby stores", "transactions", count(["baby"], 180, min_count=2)),
    Signal("childcare_started", "Childcare payments started", "transactions", onset(["childcare"], 120, 240)),
    Signal("child_benefit_started", "Child benefit payments started", "transactions",
           onset(["child_benefit"], 120, 240, direction="in")),
    Signal("photo_prints", "Photo print order", "transactions", count(["photo_print"], 90)),
    Signal("baby_pages", "Read the 'Having a baby' pages", "search", web(["baby_family"], 120)),
    Signal("child_savings_pages", "Looked at saving for a child", "search", web(["child_savings"], 120)),
    # --- home -----------------------------------------------------------------------------------
    Signal("notary_payment", "Large payment to a notary", "transactions",
           count(["legal_notary"], 180, min_amount=2000)),
    Signal("rent_stopped", "Rent payments stopped", "transactions", stopped(["rent"], 60, 180)),
    Signal("rent_started", "Rent payments started", "transactions", onset(["rent"], 90, 270)),
    Signal("rental_deposit", "Rental deposit paid", "transactions", count(["rental_deposit"], 120)),
    Signal("moving_company", "Payment to a moving company", "transactions", count(["moving_services"], 120)),
    Signal("furnishing_spike", "Unusually high furniture and DIY spending", "transactions",
           spike(["furniture", "diy_garden"], 90, 270, factor=3, min_total=1500)),
    Signal("home_loan_pages", "Looked at home loans", "search", web(["home_loan"], 150)),
    Signal("home_loan_simulator", "Used the home-loan simulator", "search", web(["home_loan"], 150, SIMULATING)),
    Signal("moving_pages", "Read the 'Moving out' pages", "search", web(["moving"], 90)),
    Signal("living_together_pages", "Read the 'Living together' pages", "search", web(["living_together"], 90)),
    # --- car ------------------------------------------------------------------------------------
    Signal("car_dealer_payment", "Large payment to a car dealer", "transactions",
           count(["car_dealer"], 90, min_amount=1000)),
    Signal("fuel_started", "Fuel spending started", "transactions", onset(["fuel"], 90, 270, min_count=2)),
    Signal("car_loan_pages", "Looked at car loans or car insurance", "search", web(["car_loan", "car_insurance"], 90)),
    Signal("car_loan_simulator", "Used the car-loan simulator", "search", web(["car_loan"], 90, SIMULATING)),
    # --- work and income ------------------------------------------------------------------------
    Signal("salary_started", "A salary started to arrive", "transactions",
           onset(["salary"], 120, 240, direction="in")),
    Signal("salary_stopped", "Salary payments stopped", "transactions",
           stopped(["salary"], 60, 180, direction="in")),
    Signal("new_employer", "Salary from a new employer", "transactions",
           Rule("new_payer", _cats("salary"), "in", 120, 240)),
    Signal("unemployment_started", "Unemployment benefit started", "transactions",
           onset(["unemployment_benefit"], 120, 240, direction="in")),
    Signal("pension_started", "Pension payments started", "transactions",
           onset(["pension"], 180, 270, direction="in")),
    Signal("insurance_payout", "Large insurance payout received", "transactions",
           count(["insurance"], 180, min_amount=10_000, direction="in")),
    Signal("first_job_pages", "Read the 'Your first job' pages", "search", web(["first_job"], 120)),
    Signal("job_loss_pages", "Read the 'Losing your job' pages", "search", web(["job_loss"], 90)),
    Signal("retirement_pages", "Read the 'Preparing your retirement' pages", "search", web(["retirement"], 180)),
    # --- other life moments ---------------------------------------------------------------------
    Signal("wedding_services", "Payments to wedding services", "transactions", count(["wedding_services"], 240)),
    Signal("jewelry_purchase", "Jewellery purchase", "transactions", count(["jewelry"], 240, min_amount=500)),
    Signal("wedding_pages", "Read the 'Getting married' pages", "search", web(["wedding"], 180)),
    Signal("notary_inflow", "Large transfer received from a notary", "transactions",
           count(["legal_notary"], 180, min_amount=5000, direction="in")),
    Signal("inheritance_pages", "Read the 'Receiving an inheritance' pages", "search", web(["inheritance"], 180)),
    Signal("separation_pages", "Read the 'Separating' pages", "search", web(["separation"], 120)),
    Signal("tuition_paid", "University fees paid", "transactions", count(["education"], 120, min_amount=200)),
    Signal("studying_pages", "Read the 'Children going to university' pages", "search", web(["studying"], 120)),
    # --- travel ---------------------------------------------------------------------------------
    Signal("flight_booked", "Flight booked", "transactions", count(["travel_flight"], 90)),
    Signal("stay_booked", "Accommodation or package holiday booked", "transactions",
           count(["travel_lodging", "travel_agency"], 90)),
    Signal("paying_abroad", "Card payments abroad", "transactions", Rule("abroad", window=21, min_count=3)),
    Signal("travel_pages", "Read about paying abroad or travel insurance", "search", web(["travel"], 60)),
    # --- told by the customer -------------------------------------------------------------------
    Signal("declared", "Situation you told us about", "declared", declared()),
]}

EVENTS = [
    Event("birth", "A baby on the way or just born", True,
          ("child_savings", "hospitalisation_insurance", "family_liability_insurance"),
          {"declared": 0.5, "baby_purchases": 0.3, "child_benefit_started": 0.4, "childcare_started": 0.3,
           "photo_prints": 0.05, "baby_pages": 0.2, "child_savings_pages": 0.1}, (180, 196),
          declared_valid_days=330),       # declared during pregnancy, true until the baby is 6 months old
    Event("home_purchase", "Buying a home", False, ("home_loan", "home_insurance"),
          {"declared": 0.5, "notary_payment": 0.45, "rent_stopped": 0.2, "moving_company": 0.15,
           "furnishing_spike": 0.15, "home_loan_pages": 0.15, "home_loan_simulator": 0.25}, (120, 180)),
    Event("car_purchase", "Buying a car", False, ("car_loan", "car_insurance"),
          {"car_dealer_payment": 0.55, "fuel_started": 0.2, "car_loan_pages": 0.15, "car_loan_simulator": 0.2},
          (60, 45)),
    Event("first_job", "First job", False, ("pension_savings", "savings_account", "credit_card"),
          {"salary_started": 0.55, "new_employer": 0.2, "first_job_pages": 0.15}, (150, 30)),
    Event("moving_out", "Moving out", False, ("home_insurance", "family_liability_insurance"),
          {"declared": 0.5, "rent_started": 0.4, "rental_deposit": 0.3, "moving_company": 0.1,
           "furnishing_spike": 0.1, "moving_pages": 0.15}, (90, 30)),
    Event("cohabitation", "Moving in together", False, ("joint_account", "home_insurance"),
          {"declared": 0.5, "rent_started": 0.2, "moving_company": 0.1, "living_together_pages": 0.25}, (90, 30)),
    Event("wedding", "Getting married", False, ("joint_account", "life_insurance"),
          {"declared": 0.5, "wedding_services": 0.45, "jewelry_purchase": 0.2, "wedding_pages": 0.2}, (60, 180)),
    Event("job_loss", "Job loss", True, ("budget_coaching", "payment_holiday"),
          {"declared": 0.5, "unemployment_started": 0.6, "salary_stopped": 0.3, "job_loss_pages": 0.2}, (120, 0)),
    Event("new_job", "New job", False, ("pension_savings", "savings_account"),
          {"declared": 0.5, "new_employer": 0.6}, (120, 0)),
    Event("retirement", "Retirement", False, ("investment_advice", "savings_account"),
          {"declared": 0.5, "pension_started": 0.6, "salary_stopped": 0.25, "insurance_payout": 0.2,
           "retirement_pages": 0.15}, (180, 60)),
    Event("inheritance", "Inheritance received", True, ("investment_advice",),
          {"notary_inflow": 0.6, "inheritance_pages": 0.2}, (120, 0)),
    Event("separation", "Separation", True, ("budget_coaching",),
          {"declared": 0.5, "rent_started": 0.2, "separation_pages": 0.35}, (120, 0)),
    Event("child_to_higher_education", "A child starting higher education", False,
          ("youth_account", "savings_account"),
          {"tuition_paid": 0.5, "rent_started": 0.15, "studying_pages": 0.2}, (90, 60)),
    Event("travel", "Travel coming up", False, ("travel_insurance",),
          {"flight_booked": 0.4, "stay_booked": 0.3, "paying_abroad": 0.2, "travel_pages": 0.2}, (0, 0)),
]
EVENTS_BY_ID = {e.id: e for e in EVENTS}

# Website topics reported in the `searches` block: topic -> (label, products, sensitive)
TOPICS = {
    "baby_family": ("Having a baby", ("child_savings", "hospitalisation_insurance"), True),
    "child_savings": ("Saving for a child", ("child_savings", "youth_account"), False),
    "home_loan": ("Home loans", ("home_loan", "home_insurance"), False),
    "home_insurance": ("Home insurance", ("home_insurance",), False),
    "renovation": ("Renovation", ("renovation_loan",), False),
    "car_loan": ("Car loans", ("car_loan", "car_insurance"), False),
    "car_insurance": ("Car insurance", ("car_insurance",), False),
    "pension_savings": ("Pension savings", ("pension_savings",), False),
    "long_term_savings": ("Long-term savings", ("long_term_savings",), False),
    "savings": ("Savings", ("savings_account",), False),
    "investing": ("Investing", ("investment_plan", "investment_advice"), False),
    "first_job": ("First job", ("pension_savings", "credit_card"), False),
    "moving": ("Moving out", ("home_insurance", "family_liability_insurance"), False),
    "living_together": ("Living together", ("joint_account", "home_insurance"), False),
    "wedding": ("Getting married", ("joint_account", "life_insurance"), False),
    "retirement": ("Retirement", ("investment_advice",), False),
    "studying": ("Children at university", ("youth_account",), False),
    "job_loss": ("Losing a job", ("budget_coaching", "payment_holiday"), True),
    "separation": ("Separating", ("budget_coaching",), True),
    "inheritance": ("Inheritance", ("investment_advice",), True),
    "travel": ("Travel", ("travel_insurance",), False),
    "hospitalisation": ("Hospitalisation insurance", ("hospitalisation_insurance",), False),
    "family_liability": ("Family liability insurance", ("family_liability_insurance",), False),
    "life_insurance": ("Life insurance", ("life_insurance",), False),
    "personal_loan": ("Personal loans", ("personal_loan",), False),
    "cards": ("Cards", ("credit_card",), False),
}

# How much each step says about intent, and how fast interest fades.
STEP_WEIGHT = {"landing": 0.5, "article": 0.5, "help": 0.3, "app_screen": 0.5, "product": 1.0, "life_moment": 1.0,
               "search": 1.5, "kate": 1.5, "tool": 2.5, "simulator": 3.0, "form": 4.0}
SEARCH_LOOKBACK_DAYS = 90
SEARCH_HALF_LIFE_DAYS = 14
SEARCH_SCALE = 5.0        # raw points for a score of 1 - 1/e = 0.63
SEARCH_MIN_SCORE = 0.15


def check_catalog() -> None:
    """Fail loudly if a rule reads a forbidden or unknown category, topic or step."""
    for s in SIGNALS.values():
        bad = s.rule.categories & FORBIDDEN_CATEGORIES
        if bad:
            raise ValueError(f"signal {s.id} reads forbidden categories {sorted(bad)}")
        unknown = s.rule.categories - CATEGORIES
        if unknown:
            raise ValueError(f"signal {s.id} reads unknown categories {sorted(unknown)}")
        if s.rule.steps - set(STEPS):
            raise ValueError(f"signal {s.id} uses unknown steps")
    for e in EVENTS:
        missing = set(e.priors) - set(SIGNALS)
        if missing:
            raise ValueError(f"event {e.id} lists unknown signals {sorted(missing)}")
    assert set(STEP_WEIGHT) == set(STEPS)


check_catalog()
