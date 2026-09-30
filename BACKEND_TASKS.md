# KBC Context: backend work split for parallel agents

> Internal work file. Every agent reads **Part A (shared context)** in full, then **only its own task** in Part C.
> The concept below **replaces "KBC Fit"** described in `KBC_Context_Tectonic_Hackathon.md`.
> Personas, figures and some rules are kept from that document (see A.4 and A.9). Everything else in it about the frontend stack is out of scope here.

---

## Table of contents

- **Part A: shared context** (every agent reads this)
  - A.1 The idea
  - A.2 Design principles (non-negotiable)
  - A.3 Stack and commands
  - A.4 The four personas
  - A.5 Project structure and file ownership
  - A.6 Domain vocabulary (frozen enums)
  - A.7 Data contracts (frozen models)
  - A.8 Engine interfaces and the pipeline
  - A.9 Formulas and initial rule tables
  - A.10 Security rules
  - A.11 Working rules for agents
- **Part B: waves and dependencies**
- **Part C: tasks T0 to T7**
- **Part D: final acceptance checklist**

---

# Part A: shared context

## A.1 The idea

We are at the Tectonic Hackathon, KBC challenge. KBC wants a bank that understands what the customer needs, recognises their situation, adapts the experience automatically, across products, at the scale of millions of customers.

Our concept, **KBC Context**, is **not a product recommendation engine**. It is one generic pipeline:

```
EVENTS        facts (transactions, KBC app behaviour, declared situations, feedback)
  ↓
SIGNALS       interpretations of facts, each with a strength and evidence
  ↓
CONTEXT       Active Moments with a confidence and a TTL ("what is happening in their life?")
  ↓
INTENTS       several probable needs at once, each with a confidence ("what do they want to achieve?")
  ↓
DECISION      scoring + suppression rules ("what should KBC do right now? maybe nothing")
  ↓
JOURNEY       a reusable set of actions (guidance, service, product, appointment)
  ↓
EXPERIENCE    structured JSON the frontend renders (never HTML)
```

Key line for the pitch: **"The best recommendation is sometimes no recommendation."**

Goal for the judges: **same engine, different data, different experience**. It must be impossible to conclude "they hardcoded four pages". There is **no** `if customer_id == ...` anywhere in engine code.

**Data limitation.** KBC does **not** know which external websites a customer visits. We only use signals that plausibly exist inside KBC: transactions, KBC app/website pages, KBC simulators, KBC search, products owned, accounts, declared life events, feedback on recommendations. All data is **synthetic**.

## A.2 Design principles (non-negotiable)

1. Events are facts. Signals are interpretations. One event never becomes a definitive intent directly.
2. Signals combine into Active Moments with a **confidence** (0..1) and an **expiry**.
3. Context produces **multiple** intents (`list[Intent]`, never `customer.intent = "x"`).
4. An intent does not imply an action. The Decision Engine weighs relevance, timing, constraints.
5. A decision can be `NO_ACTION` or `WAIT`, and it must arise naturally from data.
6. Decisions select journeys; journeys produce structured experiences.
7. **Every inference keeps its evidence** (what contributed, and how much).
8. **Rules are declarative data** in `app/rules/*.py` (dicts / Pydantic models). Engines are generic loops over rules. No scattered `if/elif` per moment or per persona.
9. **Deterministic**: no LLM in the decision path. Same inputs + same `now` = same output.
10. **Pure engines**: engines take inputs and return outputs. No I/O, no global state, no `datetime.now()` inside engines (the clock is injected).
11. Sensitive situations (parenthood) are **declared** by the customer, never inferred from spending alone (kept from KBC Fit). No rule may use `age` as an input. `life_stage` may only be a small adjustment, never the sole driver.

## A.3 Stack and commands

- Python 3.12, FastAPI, Pydantic v2, pytest, httpx (TestClient). No database: in-memory repositories seeded from JSON.
- No Kafka, no microservices, no ML. Storage behind repository interfaces so it can be swapped later.
- Everything lives in `backend/` at repo root. The frontend (separate work) calls this API.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                                   # all tests
uvicorn app.main:app --reload --port 8000   # run the API, docs at /docs
```

Code, comments, identifiers, API texts and README: **English**.

## A.4 The four personas (figures kept from KBC Fit)

| Id | Persona | Expected moment | Expected intents | Expected primary journey | Expected decision |
|---|---|---|---|---|---|
| `lucas` | Lucas, 24, first salary | `FIRST_SALARY` ≥ 0.80 | `BUILD_FINANCIAL_SAFETY` ≥ 0.85, `START_SAVING` ≥ 0.70, `START_INVESTING` ≤ 0.40 | `FINANCIAL_FOUNDATION` | `SHOW_JOURNEY`, level `PROACTIVE` |
| `julie` | Julie, 31, first child (**declared** by her) | `NEW_PARENT` ≥ 0.80 | `CHILD_SAVING`, `HOUSEHOLD_BUDGET_ADAPTATION`, `FAMILY_PROTECTION` | `FAMILY_START` | `SHOW_JOURNEY` |
| `marc` | Marc, 66, just retired | `RETIREMENT_TRANSITION` ≥ 0.80 | `INCOME_REORGANIZATION`, `SAVINGS_MANAGEMENT`, `LONG_TERM_FINANCIAL_PLANNING` | `RETIREMENT_TRANSITION` | `SHOW_JOURNEY` |
| `claire` | Claire, 38, already well covered | none active | none above threshold | none | `NO_ACTION`, experience mode `CALM`, "Everything looks on track." |

Persona facts (T1 builds data that produces exactly these figures with the A.9 formulas):

- **Lucas**: young professional, salaried, tenant, single, 0 children, savings low, beginner. Current account **€3,280**, savings account **€1,800**. First salary **+€2,450** from "Employer SA" 2 days ago, **no salary in the 180 days before** (student job income categorised `other_income`). Average monthly spending ≈ **€1,600** (rent €750 + groceries + transport + leisure). No travel insurance, no pension savings. Numbers expected in his journey: pension goal about **€110/month to reach €100,000 at 64**, "without changing anything: **6%** of the goal".
- **Julie**: employed, salaried, homeowner with mortgage, partner, 0 children yet. Current **€2,900**, savings **€2,400**, salary €3,100/month, spending ≈ €2,500/month incl. mortgage payment. **Declared** "expecting a child" 10 days ago (`DECLARED_LIFE_EVENT`), then 3 purchases in category `baby_supplies`, viewed KBC page `child_savings`. Products: current, savings, mortgage, home insurance. No child savings, no family insurance. Expected: about **€60/month to reach €20,000 by the child's 18th birthday**, "without changing anything: **21%**".
- **Marc**: retired, homeowner, no mortgage, partner. Current account **€54,400**, no savings account, very few movements. Salary history until ~75 days ago, then **recurring pension €2,450** received for the last 2 months. Spending ≈ **€2,400/month**. Products: current, home insurance. Expected: **€40,000 idle** above a **€14,400 cushion** (6 months), **74%** of the liquid balance inactive; next step "Prepare an advisor appointment".
- **Claire**: employed, salaried (€3,900 for years), homeowner, mortgage under control, partner, 1 child. Current €4,000, savings **€18,000**, spending ≈ €3,000. Products: current, savings, mortgage, home insurance, car insurance, **travel insurance**, family insurance, pension savings, investment plan, child savings. Only routine transactions. Must produce `NO_ACTION` naturally.

Extra demo scenarios (applied on top of a persona, see T1 and T6):

| Scenario id | Persona | Steps | Expected |
|---|---|---|---|
| `electric_car` | claire | 1: automotive transaction (EV dealership deposit €500). 2: page view `electric_car_loan`. 3: simulation `electric_car_loan` €25,000 / 60 months. 4: KBC search "electric car loan" | After step 1: `CAR_PROJECT` 0.25, status `EMERGING`, decision `WAIT`. After step 3: ≥ 0.80, journey `CAR_PROJECT`, car insurance action `ALREADY_COVERED` (never sold) |
| `travel_covered` | claire | airline tx + hotel tx + page `card_abroad_settings` | `TRAVEL` active, `TRAVEL_READY` shown as `SHOW_SERVICE` with notice "You're already covered for your trip", no available travel insurance product action |
| `travel_uncovered` | lucas | airline tx + hotel tx | `TRAVEL_READY` candidate includes travel insurance action `AVAILABLE` |
| `cashflow_shock` | lucas | 1: page `investment_info` + simulation `investment_plan` + search "start investing". 2: `unexpected_expense` −€1,500 (garage repair) | After 1: `START_INVESTING` ≥ 0.80, `INVESTMENT_START` in primary or secondary. After 2: `CASHFLOW_PRESSURE` ≥ 0.70, primary `CASHFLOW_SUPPORT` (`SHOW_WARNING`), `INVESTMENT_START` in `suppressed` with rule `CASHFLOW_RISK` |
| `not_relevant` | lucas | feedback `NOT_RELEVANT` on `FINANCIAL_FOUNDATION` | `FINANCIAL_FOUNDATION` in `suppressed` with rule `FEEDBACK_DISMISSED`, no longer primary |

## A.5 Project structure and file ownership

Only the owner edits a file. T0 creates every file (possibly as a stub); later owners fill them.

```
backend/
├── pyproject.toml                      T0
├── README.md                           T7
├── Dockerfile                          T7 (optional, Cloud Run friendly)
├── app/
│   ├── main.py                         T5 (T0 creates minimal app with /health)
│   ├── core/
│   │   ├── clock.py                    T0   Clock protocol, SystemClock, FixedClock
│   │   ├── config.py                   T0   Settings from env (pydantic-settings or os.environ)
│   │   └── errors.py                   T5   exception handlers, error JSON
│   ├── models/                         T0 (frozen contract, see A.7)
│   │   ├── common.py  customer.py  event.py  signal.py  snapshot.py
│   │   ├── context.py  intent.py  decision.py  journey.py  experience.py  pipeline.py
│   ├── rules/
│   │   ├── schema.py                   T0   Pydantic types of rule definitions
│   │   ├── signals.py                  T2
│   │   ├── moments.py                  T3
│   │   ├── intents.py                  T3
│   │   ├── decisions.py                T4   weights, thresholds, suppression rules
│   │   ├── journeys.py                 T4   journey catalog
│   │   └── copy.py                     T4   texts / templates for the experience
│   ├── engines/
│   │   ├── financial_snapshot.py       T2
│   │   ├── signal_engine.py            T2
│   │   ├── scoring.py                  T3   generic weighted aggregation with evidence
│   │   ├── context_engine.py           T3
│   │   ├── intent_engine.py            T3
│   │   ├── calculators.py              T4   savings goal, idle cash, loan monthly payment
│   │   ├── decision_engine.py          T4
│   │   └── experience_builder.py       T4
│   ├── services/
│   │   └── personalization_service.py  T0 skeleton (run_pipeline), T5 service class
│   ├── repositories/
│   │   ├── base.py                     T0   repository protocols
│   │   ├── memory.py                   T0   in-memory implementations (thread-safe)
│   │   └── seed_loader.py              T1
│   ├── api/
│   │   ├── deps.py                     T5   resolve_customer dependency, demo-mode guard
│   │   ├── customers.py  events.py  feedback.py  scenarios.py   T5
│   └── data/
│       ├── customers.json              T1
│       ├── events.json                 T1   seed history per persona
│       └── scenarios.json              T1   demo scenarios (A.4 table)
└── tests/
    ├── conftest.py                     T0   fixtures: fixed clock, builders
    ├── test_models.py                  T0
    ├── test_seed_data.py               T1
    ├── test_financial_snapshot.py      T2
    ├── test_signal_engine.py           T2
    ├── test_context_engine.py          T3
    ├── test_intent_engine.py           T3
    ├── test_calculators.py             T4
    ├── test_decision_engine.py         T4
    ├── test_experience_builder.py      T4
    ├── test_api.py  test_security.py   T5
    ├── test_personas_e2e.py            T6
    └── test_scenarios_e2e.py           T6
docs/
    ├── backend-architecture.md         T7
    └── api-examples.md                 T7
```

## A.6 Domain vocabulary (frozen enums)

Defined by T0 in `app/models/common.py` as `StrEnum`s. Agents may **add** members if needed (tell T6/T7 in the report). Never rename or remove.

**EventType**: `TRANSACTION`, `PAGE_VIEW`, `SIMULATION`, `KBC_SEARCH`, `PRODUCT_OPENED`, `DECLARED_LIFE_EVENT`, `RECOMMENDATION_FEEDBACK`, `JOURNEY_INTERACTION`

**TransactionCategory**: `salary`, `pension`, `other_income`, `refund`, `rent`, `mortgage_payment`, `loan_repayment`, `groceries`, `utilities`, `transport`, `leisure`, `restaurants`, `airline`, `hotel`, `automotive`, `childcare`, `baby_supplies`, `insurance_premium`, `savings_transfer`, `investment`, `unexpected_expense`, `other`

**KbcPage** (pages inside KBC app / kbc.be only): `electric_car_loan`, `car_loan`, `car_insurance`, `mortgage`, `home_insurance`, `travel_insurance`, `card_abroad_settings`, `investment_info`, `pension_savings`, `child_savings`, `family_insurance`, `budgeting_tools`, `retirement_planning`, `savings_accounts`

**SimulationType**: `electric_car_loan`, `car_loan`, `mortgage`, `pension_savings`, `investment_plan`, `savings_plan`

**ProductType**: `current_account`, `savings_account`, `child_savings_account`, `pension_savings`, `investment_plan`, `mortgage`, `car_loan`, `consumer_loan`, `credit_card`, `debit_card`, `home_insurance`, `car_insurance`, `travel_insurance`, `family_insurance`, `life_insurance`

**LifeEventDeclared**: `expecting_child`, `child_born`, `retiring`, `moving`, `new_job`

**FeedbackType**: `NOT_RELEVANT`, `LATER`, `USEFUL`

**SignalType**
- from single events (T2 event rules): `SALARY_RECEIVED`, `PENSION_RECEIVED`, `AIR_TRAVEL_ACTIVITY`, `HOTEL_BOOKING`, `TRAVEL_PAGE_VIEW`, `FOREIGN_PAYMENT_SETTINGS_VIEWED`, `AUTOMOTIVE_TRANSACTION`, `ELECTRIC_CAR_LOAN_PAGE_VIEW`, `ELECTRIC_CAR_LOAN_SIMULATION`, `CAR_FINANCING_KBC_SEARCH`, `MORTGAGE_PAGE_VIEW`, `MORTGAGE_SIMULATION`, `HOME_KBC_SEARCH`, `INVESTMENT_PAGE_VIEW`, `INVESTMENT_SIMULATION`, `INVESTMENT_KBC_SEARCH`, `CHILD_SAVINGS_PAGE_VIEW`, `CHILD_ACCOUNT_OPENED`, `CHILD_RELATED_EXPENSE`, `PARENTHOOD_DECLARED`, `RETIREMENT_DECLARED`, `RETIREMENT_PAGE_VIEW`, `LARGE_UNEXPECTED_EXPENSE`, `LARGE_CASH_INFLOW`, `SAVINGS_TRANSFER`
- from patterns over history + snapshot (T2 pattern detectors): `FIRST_RECURRING_SALARY`, `SALARY_STOPPED`, `RECURRING_PENSION_STARTED`, `NEW_RECURRING_CHILD_EXPENSES`, `REPEATED_MORTGAGE_SIMULATION`, `LOW_PROJECTED_BALANCE`, `LOW_EMERGENCY_BUFFER`, `HIGH_IDLE_CASH`

**MomentType**: `FIRST_SALARY`, `NEW_PARENT`, `RETIREMENT_TRANSITION`, `TRAVEL`, `CAR_PROJECT`, `HOME_BUYING`, `CASHFLOW_PRESSURE`, `LARGE_CASH_INFLOW`, `INVESTMENT_INTEREST`

**IntentType**: `BUILD_FINANCIAL_SAFETY`, `START_SAVING`, `LEARN_BUDGETING`, `START_INVESTING`, `CHILD_SAVING`, `HOUSEHOLD_BUDGET_ADAPTATION`, `FAMILY_PROTECTION`, `INCOME_REORGANIZATION`, `SAVINGS_MANAGEMENT`, `LONG_TERM_FINANCIAL_PLANNING`, `PREPARE_TRIP`, `FINANCE_CAR`, `PROTECT_CAR`, `BUY_HOME`, `STABILIZE_CASHFLOW`

**JourneyType**: `FINANCIAL_FOUNDATION`, `FAMILY_START`, `RETIREMENT_TRANSITION`, `TRAVEL_READY`, `CAR_PROJECT`, `HOME_BUYING`, `CASHFLOW_SUPPORT`, `INVESTMENT_START`

**JourneyKind**: `SUPPORT` (protects the customer, may be urgent), `GUIDANCE` (helps plan, low commercial pressure), `COMMERCIAL` (leads to a product)

**DecisionType**: `SHOW_JOURNEY`, `SHOW_GUIDANCE`, `SHOW_PRODUCT`, `SHOW_SERVICE`, `SHOW_WARNING`, `PASSIVE_PERSONALIZATION`, `WAIT`, `NO_ACTION`

**DecisionLevel**: `PROACTIVE` (score ≥ 0.80), `SUGGESTION` (0.60–0.80), `PASSIVE` (0.40–0.60), `NONE` (< 0.40)

**ActionKind**: `INFO`, `SIMULATION`, `PRODUCT`, `SERVICE`, `APPOINTMENT`, `SETTINGS`, `EDUCATION`
**ActionStatus**: `AVAILABLE`, `ALREADY_COVERED`, `HIDDEN`

**MomentStatus**: `ACTIVE` (confidence ≥ 0.40), `EMERGING` (0.20 ≤ c < 0.40). Below 0.20 the moment is not returned.

## A.7 Data contracts (frozen models)

Pydantic v2, `model_config = ConfigDict(extra="forbid")` on every **input** model, `frozen=True` where convenient. Money: `float` rounded to 2 decimals, EUR only (PoC simplification, stated in README limitations). All datetimes timezone-aware UTC.

```python
# common.py
CustomerId = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{1,31}$")]

class Evidence(BaseModel):
    kind: Literal["signal", "moment", "profile", "product", "feedback", "financial", "rule"]
    ref: str                    # e.g. "ELECTRIC_CAR_LOAN_SIMULATION", "travel_insurance", "CASHFLOW_RISK"
    contribution: float         # signed; 0 for pure facts
    detail: str                 # short human sentence, English
    source_event_ids: list[str] = []

# customer.py
class Employment(BaseModel):   status: Literal["employed","self_employed","unemployed","retired","student"]; type: Literal["salaried","freelance","none"]
class Housing(BaseModel):      status: Literal["tenant","homeowner","living_with_parents"]; mortgage: bool
class Family(BaseModel):       status: Literal["single","partner","married"]; children: int = Field(ge=0, le=20)
class FinancialProfile(BaseModel):
    savings_level: Literal["low","medium","high"]
    income_stability: Literal["stable","variable","none"]
    financial_maturity: Literal["beginner","intermediate","experienced"]
class CustomerProfile(BaseModel):          # composable persistent attributes, NOT a segment
    life_stage: Literal["student","young_professional","established","family","pre_retirement","retired"]
    employment: Employment
    income_stage: Literal["none","first_recurring_salary","established","pension"]
    housing: Housing
    family: Family
    financial_profile: FinancialProfile
class Consent(BaseModel):      personalization: bool = True
class Account(BaseModel):
    id: str; type: Literal["current","savings","child_savings","pension_savings","investment"]
    label: str; masked_number: str          # "•••• 4821", fake
    balance: float                          # balance at seed time
    currency: Literal["EUR"] = "EUR"
class OwnedProduct(BaseModel):
    product: ProductType; since: date
    details: dict[str, str | float | bool] = {}   # e.g. {"coverage": "worldwide"}
class Customer(BaseModel):
    id: CustomerId; first_name: str; age: int     # age is display only, never a rule input
    profile: CustomerProfile; accounts: list[Account]; products: list[OwnedProduct]; consent: Consent

# event.py  (discriminated union on `type`)
class TransactionData(BaseModel):
    direction: Literal["in","out"]; amount: float = Field(gt=0, le=1_000_000)
    currency: Literal["EUR"] = "EUR"; category: TransactionCategory
    merchant: str = Field(min_length=1, max_length=80); account_id: str | None = None
    recurring: bool = False
class PageViewData(BaseModel):          page: KbcPage
class SimulationData(BaseModel):        simulation_type: SimulationType; amount: float | None = Field(None, gt=0, le=5_000_000); duration_months: int | None = Field(None, ge=1, le=480)
class KbcSearchData(BaseModel):         query: str = Field(min_length=1, max_length=100)   # stripped, control chars rejected
class ProductOpenedData(BaseModel):     product: ProductType
class DeclaredLifeEventData(BaseModel): life_event: LifeEventDeclared
class FeedbackData(BaseModel):          journey: JourneyType; feedback: FeedbackType
class JourneyInteractionData(BaseModel):journey: JourneyType; action_id: str = Field(max_length=64, pattern=r"^[A-Z0-9_]+$")

class _EventBase(BaseModel):
    id: str; customer_id: CustomerId; timestamp: datetime
    origin: Literal["seed","live"]          # live = posted through the API after seed
class TransactionEvent(_EventBase):  type: Literal[EventType.TRANSACTION];  data: TransactionData
# ... one subclass per EventType ...
CustomerEvent = Annotated[Union[TransactionEvent, PageViewEvent, ...], Field(discriminator="type")]

# API input: same union WITHOUT id / customer_id / timestamp / origin (server sets them)
class EventIn...  -> `EventInput` discriminated union, each with optional `days_ago: int = Field(0, ge=0, le=365)` (demo time travel)

# signal.py
class Signal(BaseModel):
    type: SignalType; strength: float = Field(ge=0, le=1); timestamp: datetime
    expires_at: datetime | None
    source: Literal["event","pattern"]; source_event_ids: list[str]
    description: str                         # "Airline payment of €420 (Brussels Airlines)"

# snapshot.py
class FinancialSnapshot(BaseModel):
    as_of: datetime
    current_balance: float; savings_balance: float; liquid_balance: float
    monthly_income: float; income_sources: list[Literal["salary","pension","other"]]
    avg_monthly_spending: float
    next_income_date: date | None; days_until_next_income: int
    projected_balance_before_next_income: float
    emergency_buffer_months: float
    idle_cash: float; idle_ratio: float
    monthly_debt_payments: float; debt_ratio: float
    monthly_margin: float                    # monthly_income - avg_monthly_spending

# context.py
class ActiveMoment(BaseModel):
    type: MomentType; confidence: float; status: MomentStatus
    detected_at: datetime; expires_at: datetime; evidence: list[Evidence]
class CustomerContext(BaseModel):
    persistent: CustomerProfile; products: list[ProductType]
    snapshot: FinancialSnapshot; signals: list[Signal]; moments: list[ActiveMoment]

# intent.py
class Intent(BaseModel):
    type: IntentType; confidence: float; related_moments: list[MomentType]; evidence: list[Evidence]

# journey.py  (definition lives in rules/journeys.py, instance in experience)
class JourneyActionDef(BaseModel):
    id: str; kind: ActionKind; label: str
    product: ProductType | None = None       # if set and owned -> ALREADY_COVERED
    calculator: str | None = None            # name of a calculators.py function feeding payload
class JourneyDef(BaseModel):
    type: JourneyType; title: str; kind: JourneyKind
    serves_intents: dict[IntentType, float]  # relevance of this journey for each intent (0..1)
    usefulness: float                        # base usefulness 0..1
    urgent: bool = False                     # SUPPORT journeys may be urgent
    eligibility: list[Condition] = []        # see rules/schema.py
    actions: list[JourneyActionDef]

# decision.py
class ScoreBreakdown(BaseModel):
    intent_confidence: float; timing_relevance: float; usefulness: float
    eligibility: float; financial_fit: float; penalties: float
    weights: dict[str, float]; total: float
class JourneyCandidate(BaseModel):
    journey: JourneyType; driven_by: list[IntentType]; score: float
    breakdown: ScoreBreakdown; decision_type: DecisionType; evidence: list[Evidence]
class SuppressedCandidate(BaseModel):
    journey: JourneyType; rule: str; reason: str; score_before: float
class Decision(BaseModel):
    decision_type: DecisionType; level: DecisionLevel
    primary: JourneyCandidate | None; secondary: list[JourneyCandidate]   # max 2
    considered: list[JourneyCandidate]; suppressed: list[SuppressedCandidate]
    reasons: list[str]; decided_at: datetime

# experience.py
class ExperienceAction(BaseModel):
    id: str; kind: ActionKind; label: str; status: ActionStatus
    payload: dict[str, float | int | str | bool] = {}
class Hero(BaseModel):          type: str; title: str; subtitle: str; tone: Literal["calm","positive","attention","warning"]
class JourneyCard(BaseModel):   type: JourneyType; title: str; priority: float; decision_type: DecisionType; actions: list[ExperienceAction]
class Notice(BaseModel):        kind: Literal["reassurance","warning","info"]; text: str
class WhyItem(BaseModel):       text: str; contribution: float
class CheckItem(BaseModel):     label: str; ok: bool; detail: str     # "what we checked" (calm mode)
class UnderTheHood(BaseModel):
    persistent_context: CustomerProfile; products: list[ProductType]; snapshot: FinancialSnapshot
    signals: list[Signal]; moments: list[ActiveMoment]; intents: list[Intent]; decision: Decision
    timing: dict[str, str]                  # e.g. {"computed_at": ..., "FIRST_SALARY_expires_at": ...}
class PersonalizedExperience(BaseModel):
    customer_id: CustomerId; mode: Literal["PROACTIVE","SUGGESTION","PASSIVE","WAIT","CALM"]
    hero: Hero; primary_journey: JourneyCard | None; secondary_journeys: list[JourneyCard]
    notices: list[Notice]; why: list[WhyItem]; checks: list[CheckItem]
    under_the_hood: UnderTheHood; generated_at: datetime; disclaimer: str

# pipeline.py
class PipelineResult(BaseModel):
    customer: Customer; context: CustomerContext; intents: list[Intent]
    decision: Decision; experience: PersonalizedExperience
```

## A.8 Engine interfaces and the pipeline

Every engine is a class with rules injected in the constructor (default = the module's rules), so tests can pass custom rules.

```python
compute_snapshot(customer, events, now) -> FinancialSnapshot                       # T2, pure function
SignalEngine(rules).extract(event, now) -> list[Signal]                             # T2, one event
SignalEngine(rules).detect_patterns(customer, events, snapshot, now) -> list[Signal]# T2, history-based
SignalEngine(rules).extract_all(customer, events, snapshot, now) -> list[Signal]    # T2, both, drops expired
ContextEngine(rules).compute(customer, signals, now) -> list[ActiveMoment]          # T3
IntentEngine(rules).compute(customer, moments, signals, now) -> list[Intent]        # T3
DecisionEngine(rules, journeys).decide(customer, snapshot, moments, intents, events, now) -> Decision   # T4
ExperienceBuilder(journeys, copy).build(customer, context, intents, decision, now) -> PersonalizedExperience  # T4

# services/personalization_service.py (T0 writes it, T5 extends)
def run_pipeline(customer, events, now, engines=DEFAULT_ENGINES) -> PipelineResult:
    if not customer.consent.personalization: -> empty signals/moments/intents, Decision NO_ACTION reason "NO_CONSENT"
    snapshot = compute_snapshot(customer, events, now)
    signals  = signal_engine.extract_all(customer, events, snapshot, now)
    moments  = context_engine.compute(customer, signals, now)
    intents  = intent_engine.compute(customer, moments, signals, now)
    decision = decision_engine.decide(customer, snapshot, moments, intents, events, now)
    experience = experience_builder.build(customer, context, intents, decision, now)
```

State is **recomputed from the event log** on every read (pure function of profile + events + now). This is the scaling argument: per-customer, no shared state, horizontally partitionable by customer id; in production the same engines would run incrementally on an event stream.

## A.9 Formulas and initial rule tables

These are the **starting values**. T6 may tune weights so persona tests pass; any change must keep the A.4 expectations.

### Financial snapshot (T2)

- Balances: `current_balance` = seed balance of current account(s) + Σ signed amounts of **live** `TRANSACTION` events (in = +, out = −). `savings_balance` = seed balance of savings accounts. `liquid_balance` = current + savings.
- `monthly_income` = Σ incoming `salary` + `pension` in the last 30 days.
- `avg_monthly_spending` = Σ outgoing transactions in the last 90 days, **excluding** `savings_transfer`, `investment`, `unexpected_expense`, divided by 3.
- `next_income_date` = latest salary/pension date + 30 days. `days_until_next_income` = clamp(days, 0, 30).
- `projected_balance_before_next_income` = `current_balance − avg_monthly_spending × days_until_next_income / 30`.
- `emergency_buffer_months` = `(savings_balance + max(0, current_balance − avg_monthly_spending)) / avg_monthly_spending`.
- `idle_cash` = `max(0, liquid_balance − 6 × avg_monthly_spending)`; `idle_ratio` = idle_cash / liquid_balance.
- `monthly_debt_payments` = Σ outgoing `mortgage_payment` + `loan_repayment` in the last 30 days; `debt_ratio` = / monthly_income (0 if no income).
- `monthly_margin` = monthly_income − avg_monthly_spending.

Sanity values: Lucas buffer ≈ 2.2 months, projected ≈ 1,787 → after −€1,500 shock ≈ 287. Marc idle = 54,400 − 14,400 = 40,000, ratio 0.74. Claire buffer ≈ 6.3.

### Pattern signals (T2, thresholds live in `rules/signals.py`)

| Signal | Condition | Strength |
|---|---|---|
| `FIRST_RECURRING_SALARY` | a `salary` credit in the last 30 days AND no `salary` credit in the 180 days before it | 1.0 |
| `SALARY_STOPPED` | salary credits existed 60–180 days ago, none in the last 45 days | 1.0 |
| `RECURRING_PENSION_STARTED` | ≥ 1 `pension` credit in last 45 days AND no pension credit before 90 days ago | 1.0 |
| `NEW_RECURRING_CHILD_EXPENSES` | ≥ 3 `baby_supplies`/`childcare` debits in last 60 days, none before | 0.8 |
| `REPEATED_MORTGAGE_SIMULATION` | ≥ 3 mortgage simulations in 30 days | 1.0 |
| `LOW_PROJECTED_BALANCE` | projected < 500 OR projected < 0.3 × avg_monthly_spending | 1.0 |
| `LOW_EMERGENCY_BUFFER` | emergency_buffer_months < 3 | 1.0 |
| `HIGH_IDLE_CASH` | idle_cash ≥ 10,000 AND idle_ratio ≥ 0.5 | 1.0 |

Event signals: `LARGE_UNEXPECTED_EXPENSE` = `unexpected_expense` debit ≥ €500; `LARGE_CASH_INFLOW` = `other_income`/`refund` credit ≥ €5,000; `AIR_TRAVEL_ACTIVITY` strength 0.8 (ambiguous: could be a gift). Default signal TTL: 60 days, configurable per type.

### Moment rules (T3, `rules/moments.py`)

Confidence = min(1, Σ over rule signals of `weight × strongest strength of that signal type`) within the moment's window (`ttl_days` before `now`). Same signal type counted once (the strongest). If `requires_any` is set and none present, confidence is capped at `cap_without_required`.

| Moment | Signal weights | TTL days | Extra |
|---|---|---|---|
| `FIRST_SALARY` | FIRST_RECURRING_SALARY 0.70, SALARY_RECEIVED 0.15, LOW_EMERGENCY_BUFFER 0.10 | 90 | |
| `NEW_PARENT` | PARENTHOOD_DECLARED 0.55, CHILD_ACCOUNT_OPENED 0.25, CHILD_RELATED_EXPENSE 0.20, NEW_RECURRING_CHILD_EXPENSES 0.15, CHILD_SAVINGS_PAGE_VIEW 0.10 | 180 | requires_any [PARENTHOOD_DECLARED, CHILD_ACCOUNT_OPENED], cap 0.35 |
| `RETIREMENT_TRANSITION` | RECURRING_PENSION_STARTED 0.45, SALARY_STOPPED 0.35, RETIREMENT_DECLARED 0.30, RETIREMENT_PAGE_VIEW 0.10, HIGH_IDLE_CASH 0.10 | 180 | |
| `TRAVEL` | AIR_TRAVEL_ACTIVITY 0.35, HOTEL_BOOKING 0.25, TRAVEL_PAGE_VIEW 0.20, FOREIGN_PAYMENT_SETTINGS_VIEWED 0.20 | 30 | |
| `CAR_PROJECT` | AUTOMOTIVE_TRANSACTION 0.25, ELECTRIC_CAR_LOAN_PAGE_VIEW 0.30, ELECTRIC_CAR_LOAN_SIMULATION 0.30, CAR_FINANCING_KBC_SEARCH 0.15 | 60 | |
| `HOME_BUYING` | MORTGAGE_SIMULATION 0.35, REPEATED_MORTGAGE_SIMULATION 0.25, MORTGAGE_PAGE_VIEW 0.25, HOME_KBC_SEARCH 0.15 | 90 | |
| `CASHFLOW_PRESSURE` | LOW_PROJECTED_BALANCE 0.55, LARGE_UNEXPECTED_EXPENSE 0.35, LOW_EMERGENCY_BUFFER 0.10 | 14 | |
| `LARGE_CASH_INFLOW` | LARGE_CASH_INFLOW 0.80, HIGH_IDLE_CASH 0.20 | 60 | |
| `INVESTMENT_INTEREST` | INVESTMENT_SIMULATION 0.40, INVESTMENT_PAGE_VIEW 0.30, INVESTMENT_KBC_SEARCH 0.20 | 45 | |

`detected_at` = earliest contributing signal; `expires_at` = latest contributing signal + ttl. Optional `decay: "none" | "linear"` per rule (default none).

### Intent rules (T3, `rules/intents.py`)

Confidence = clamp(Σ `weight × moment.confidence` over **ACTIVE** moments + Σ `weight × signal.strength` + profile adjustments, 0, 1). Intents below 0.10 are dropped (low intents stay visible "under the hood", e.g. Lucas START_INVESTING ≈ 0.14). Profile adjustments are `(path, equals, delta)` triples; paths starting with `age` are **forbidden** (a test asserts it).

| Intent | From moments | From signals | Profile adjustments |
|---|---|---|---|
| `BUILD_FINANCIAL_SAFETY` | FIRST_SALARY 0.75, CASHFLOW_PRESSURE 0.40 | LOW_EMERGENCY_BUFFER 0.25 | |
| `START_SAVING` | FIRST_SALARY 0.70, NEW_PARENT 0.20 | LOW_EMERGENCY_BUFFER 0.15 | |
| `LEARN_BUDGETING` | FIRST_SALARY 0.50, NEW_PARENT 0.20 | | financial_maturity=beginner +0.10 |
| `START_INVESTING` | INVESTMENT_INTEREST 0.80, FIRST_SALARY 0.20, LARGE_CASH_INFLOW 0.40 | | financial_maturity=beginner −0.05 |
| `CHILD_SAVING` | NEW_PARENT 0.85 | CHILD_SAVINGS_PAGE_VIEW 0.10 | |
| `HOUSEHOLD_BUDGET_ADAPTATION` | NEW_PARENT 0.75 | | |
| `FAMILY_PROTECTION` | NEW_PARENT 0.70 | | |
| `INCOME_REORGANIZATION` | RETIREMENT_TRANSITION 0.85 | | |
| `SAVINGS_MANAGEMENT` | RETIREMENT_TRANSITION 0.70, LARGE_CASH_INFLOW 0.50 | HIGH_IDLE_CASH 0.25 | |
| `LONG_TERM_FINANCIAL_PLANNING` | RETIREMENT_TRANSITION 0.70 | | |
| `PREPARE_TRIP` | TRAVEL 0.90 | | |
| `FINANCE_CAR` | CAR_PROJECT 0.80 | ELECTRIC_CAR_LOAN_SIMULATION 0.15 | |
| `PROTECT_CAR` | CAR_PROJECT 0.40 | | |
| `BUY_HOME` | HOME_BUYING 0.90 | | |
| `STABILIZE_CASHFLOW` | CASHFLOW_PRESSURE 0.95 | | |

### Decision scoring (T4, `rules/decisions.py`)

For each journey J and the intents it serves: `intent_confidence = max(intent.confidence × J.serves_intents[intent])`.

```
score = 0.35 × intent_confidence
      + 0.25 × timing_relevance
      + 0.20 × usefulness
      + 0.10 × eligibility
      + 0.10 × financial_fit
      − penalties
```

- `timing_relevance`: from the freshest ACTIVE moment behind the intent. `f = age / ttl` with age measured from `detected_at`. 1.0 if f ≤ 0.33, then linear to 0.3 at f = 1.
- `usefulness`: `J.usefulness`, multiplied by `(1 − 0.5 × covered_ratio)` where covered_ratio = share of the journey's product actions whose product is already owned.
- `eligibility`: 1.0 if all `J.eligibility` conditions hold, else 0 and the journey is suppressed (`NOT_ELIGIBLE`).
- `financial_fit`: `safety = 0.6 × clamp(projected / avg_spending, 0, 1) + 0.4 × clamp(buffer_months / 6, 0, 1)`. For `SUPPORT` journeys, `financial_fit = 1 − safety` (the worse the situation, the more relevant). Otherwise `financial_fit = safety`.
- `penalties`: `LATER` feedback within 7 days → 0.25.

Suppression rules (declarative list, evaluated in order, each recorded in `decision.suppressed` with `rule` and a human `reason`):

| Rule id | Condition | Effect |
|---|---|---|
| `NO_CONSENT` | consent.personalization is false | everything suppressed, `NO_ACTION` |
| `LOW_CONFIDENCE` | intent_confidence < 0.40 | candidate dropped |
| `FEEDBACK_DISMISSED` | `NOT_RELEVANT` feedback on this journey within 30 days | suppressed |
| `CASHFLOW_RISK` | CASHFLOW_PRESSURE ≥ 0.70 OR `LOW_PROJECTED_BALANCE` present | suppress every `COMMERCIAL` journey (non-urgent by definition); `SUPPORT` and `GUIDANCE` journeys stay |
| `ALREADY_COVERED` | every product action of J is owned and J has no non-product action | suppressed; otherwise actions are marked `ALREADY_COVERED` and a reassurance notice is added |
| `NOT_ELIGIBLE` | an eligibility condition fails | suppressed |

Choice: rank remaining candidates by score. Primary = best; secondary = next 2 with score ≥ 0.40.
- best ≥ 0.80 → `PROACTIVE`; 0.60–0.80 → `SUGGESTION`; 0.40–0.60 → `PASSIVE` with `PASSIVE_PERSONALIZATION`.
- no candidate ≥ 0.40: `WAIT` if any moment is `EMERGING` or the best candidate has timing < 0.4, else `NO_ACTION`.
- decision_type for PROACTIVE/SUGGESTION: `SUPPORT` → `SHOW_WARNING` (urgent) or `SHOW_GUIDANCE`; `GUIDANCE` → `SHOW_JOURNEY`; `COMMERCIAL` → `SHOW_JOURNEY`; if all product actions are `ALREADY_COVERED` → `SHOW_SERVICE`.

Journey eligibility examples: `CAR_PROJECT` loan simulation requires `monthly_income > 0`; `HOME_BUYING` requires `monthly_income > 0`; `INVESTMENT_START` requires `emergency_buffer_months ≥ 1`.

### Calculators (T4, illustrative 3%/year, **not KBC rates**, disclaimer in experience)

- `monthly_for_target(current, target, months, annual_rate=0.03)`: growth g = (1 + r/12)^n, annuity a = (g − 1)/(r/12); monthly = (target − current × g) / a, **rounded up to the next €10**, capped at 40% of `monthly_margin`. Also returns `progress_without_change = current × g / target`. Checks: Lucas (1,800 → 100,000 over 40 years) = €110, 6%. Julie (2,400 → 20,000 over 18 years) = €60, 21%.
- `idle_cash_insight(snapshot)`: cushion = 6 × avg spending, idle, ratio. Marc: 14,400 / 40,000 / 74%.
- `emergency_buffer_goal(snapshot)`: target = 3 × avg spending, gap, suggested monthly (min(10% income, 40% margin), rounded to €10).
- `loan_monthly_payment(amount, months, annual_rate=0.045)`: standard annuity, illustrative.
- `cashflow_forecast(snapshot)`: projected balance, days until income.

Pension horizon for Lucas uses a **fixed demo assumption** stored in the journey action (`horizon_years: 40`), not a rule on age.

## A.10 Security rules (a security audit, Aikido, is part of the hackathon)

- Validate every input with Pydantic (`extra="forbid"`, bounded numbers, bounded strings, enums instead of free text). Search queries: strip, reject control characters, max 100 chars; never echoed into logs.
- `customer_id` goes through **one** dependency (`resolve_customer`) that validates the pattern and looks it up in the repository. Unknown id → 404 with a neutral message. The README explains that in production the id comes from the authenticated session, never from the path (IDOR), and that `resolve_customer` is the single place to swap.
- Customer isolation: repositories are keyed by customer id; no endpoint lists another customer's events; engines only receive one customer's data.
- Server sets `id`, `timestamp`, `origin` of events. Client timestamps are never trusted (`days_ago` is demo-only and bounded).
- No secrets, no API keys, no `.env` committed (add `.gitignore`). Config via env vars only: `KBC_CORS_ORIGINS` (comma list, default `http://localhost:3000`), `KBC_DEMO_MODE` (default `true`; enables `/reset` and `/scenarios`).
- Seed files read with `json.load` from fixed paths inside the package. No `pickle`, no `eval`, no `yaml.load`, no file paths from user input.
- Error handlers return `{"error": {"code": ..., "message": ...}}`. No stack traces. 422 responses must not echo raw input values.
- Security headers middleware: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` on customer endpoints.
- Request body size limit (e.g. 16 KB) on POST endpoints. Event log per customer capped (e.g. 2,000 events) to avoid memory abuse.

## A.11 Working rules for agents

1. Read Part A fully, then your task. Do not start a task whose dependencies (Part B) are not done.
2. **Edit only the files you own** (A.5). If you need something in a file you do not own, write it in your final report under "Requests for other tasks" instead of editing.
3. Models and enums (A.6, A.7) are frozen. Allowed: **adding** an optional field or an enum member, reported in your final report. Forbidden: renaming, removing, changing types.
4. Every rule value lives in `app/rules/*`. Engines never contain moment/intent/journey names in `if` statements (except generic handling of `JourneyKind`, statuses and levels).
5. Every function you write gets tests. `pytest -q` must be green before you finish (tests of other tasks that are still stubs may be marked `xfail` by their owner only).
6. Use the fixed clock from `tests/conftest.py`. Never call `datetime.now()` outside `core/clock.py`.
7. Commit only your own files: `git add <your paths> && git commit -m "Tn: ..."` on branch `Mathias`. Do not push.
8. Final report (short): what you built, how to verify, deviations from this file, requests for other tasks.

---

# Part B: waves and dependencies

```
Wave 1 (1 agent)      T0 Foundation: skeleton + frozen models + stubs + pipeline skeleton
                        │
Wave 2 (4 agents)     T1 Data ── T2 Signals+Snapshot ── T3 Context+Intent ── T4 Decision+Journeys+Experience
   in parallel          │               │                      │                     │
                        └───────────────┴──────────┬───────────┴─────────────────────┘
Wave 3 (3 agents)     T5 API + security     T6 End-to-end tests + rule tuning     T7 README + docs
   in parallel
                                          ▼
                              Final: run Part D checklist
```

| Task | Depends on | Can run with | Estimated size |
|---|---|---|---|
| T0 | nothing | alone | M |
| T1 | T0 | T2, T3, T4 | M |
| T2 | T0 | T1, T3, T4 | L |
| T3 | T0 | T1, T2, T4 | M |
| T4 | T0 | T1, T2, T3 | L |
| T5 | T0–T4 | T6, T7 | M |
| T6 | T0–T4 (uses `run_pipeline`, not the API) | T5, T7 | M |
| T7 | T0–T4 (finalise after T5) | T5, T6 | S |

Wave 2 agents work against the **contracts** in A.7/A.8. T3 and T4 build their own `Signal` / `ActiveMoment` / `Intent` fixtures in tests; they do not wait for T2's output. Integration is proven in wave 3 by T6.

---

# Part C: tasks

## T0: Foundation (skeleton, frozen contracts, stubs)

**Prompt to give the agent:**
> You are agent T0 on the KBC Context backend. Read `BACKEND_TASKS.md` Part A fully, then do task T0. Only create/edit the files owned by T0. Follow A.11.

**Goal:** everyone else can start in parallel against stable types.

**Deliverables**
1. `backend/pyproject.toml`: fastapi, uvicorn[standard], pydantic>=2, pydantic-settings; dev extras: pytest, httpx. `[tool.pytest.ini_options]` with `testpaths = ["tests"]`. `.gitignore` entries: `.venv/`, `__pycache__/`, `.env`, `.pytest_cache/`.
2. Every directory and file of A.5 created. Files owned by later tasks contain a module docstring stating the owner ("Owner: T3") and, for engines, the class with the A.8 signature raising `NotImplementedError`.
3. `app/models/*`: **all** enums of A.6 and models of A.7, complete and validated. Event discriminated unions (stored `CustomerEvent` and API `EventInput`), with a helper `EventInput.to_event(customer_id, now, id) -> CustomerEvent` that applies `days_ago`.
4. `app/rules/schema.py`: Pydantic types for rule definitions: `SignalEventRule` (event type + match on data fields → signal type, strength, ttl_days), `PatternThresholds`, `MomentRule` (signals weights, ttl_days, requires_any, cap_without_required, decay), `IntentRule` (moment weights, signal weights, profile adjustments), `ProfileAdjustment(path, equals, delta)` with a validator rejecting paths starting with `age`, `Condition(field, op, value)` for eligibility (ops: `gt`, `ge`, `lt`, `le`, `eq`, `owns`, `not_owns`), `SuppressionRule`, `DecisionWeights`, `DecisionThresholds`.
5. `app/core/clock.py` (`Clock` protocol, `SystemClock`, `FixedClock`), `app/core/config.py` (settings from env, A.10 defaults).
6. `app/repositories/base.py` + `memory.py`: `CustomerRepository` (`get`, `list`, `update_consent`, `reset`), `EventRepository` (`list_for`, `append`, `reset`), thread-safe (`threading.Lock`), deep copies on read, per-customer event cap. They take their seed data as constructor input (T1 provides the loader).
7. `app/services/personalization_service.py`: `run_pipeline` exactly as A.8 (calls the stubbed engines, handles `NO_CONSENT` itself) + `Engines` dataclass holding default engine instances.
8. `app/main.py`: minimal FastAPI app with `GET /health`.
9. `tests/conftest.py`: `NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)`, `fixed_clock` fixture, builders `make_customer(**overrides)`, `make_event(type, data, days_ago=0, origin="seed")`, `make_signal(type, strength=1.0, days_ago=0)`, `make_moment(type, confidence, days_ago=0, ttl_days=30)`, `make_intent(type, confidence)`, `make_snapshot(**overrides)`.
10. `tests/test_models.py`: valid/invalid events (extra field rejected, negative amount rejected, bad page rejected, 101-char search rejected, bad customer id rejected, `age` profile adjustment rejected).

**Acceptance:** `pip install -e ".[dev]"` works, `pytest -q` green (engine stubs untested), `uvicorn app.main:app` serves `/health`. Commit `T0: foundation`.

---

## T1: Personas, seed history, demo scenarios

**Prompt:**
> You are agent T1 on the KBC Context backend. Read `BACKEND_TASKS.md` Part A fully (especially A.4 and A.9), then do task T1. T0 is done. Only edit files owned by T1. Follow A.11.

**Goal:** four believable, synthetic customers whose raw data **naturally** yields the A.4 expectations through the A.9 formulas. No hint in the data about the expected outcome (no field like `"expected_moment"`).

**Deliverables**
1. `app/data/customers.json`: 4 customers (A.4 facts), composable profiles, fake masked account numbers (`•••• 1234`), owned products with `since` dates, consent true.
2. `app/data/events.json`: per customer, ~90–200 days of history expressed with **relative time** (`days_ago`, optional `hour`) so the demo never goes stale. Include routine noise (groceries, utilities, transport, restaurants) so personas look real. Claire's history must be varied and healthy but contain **no** travel/car/mortgage-simulation/child signals.
   - Lucas: small `other_income` student-job credits in the past, and **no** `salary` credit before the single one 2 days ago.
   - Julie: `DECLARED_LIFE_EVENT expecting_child` 10 days ago, 3 `baby_supplies` debits in last 30 days, `PAGE_VIEW child_savings` 3 days ago, monthly `mortgage_payment`.
   - Marc: monthly `salary` from ~180 to ~75 days ago, then `pension` 2 × €2,450 (~40 and ~10 days ago), sparse spending totalling ≈ €2,400/month.
3. `app/data/scenarios.json`: the 5 scenarios of A.4, each `{id, title, description, customer_id, steps: [{label, events: [EventInput-compatible objects]}]}`.
4. `app/repositories/seed_loader.py`: `load_seed(now) -> SeedData(customers, events_by_customer, scenarios)`; resolves `days_ago` against `now`, validates everything with the A.7 models (fail loudly at startup if invalid), generates deterministic event ids (`evt_<customer>_<n>`), `origin="seed"`. Reads files with `importlib.resources` / fixed `Path(__file__)`; no user-supplied paths.
5. `tests/test_seed_data.py`: data validates; ids unique; each persona's key facts hold (Lucas has exactly one salary credit; Marc salary stops and pension starts; Julie has a declared event; Claire owns travel + car insurance); snapshot figures by hand-computing A.9 formulas in the test (do not import T2's engine): Lucas avg spending within 1,550–1,650, Marc spending ≈ 2,400 so idle = 40,000 ± 100, Claire buffer ≥ 6.
6. Also export a tiny helper `scenario_step_events(scenario_id, step_index) -> list[EventInput]` for T5/T6.

**Acceptance:** tests green; a short table in your report with each persona's computed snapshot values.

---

## T2: Financial snapshot + Signal Engine

**Prompt:**
> You are agent T2 on the KBC Context backend. Read `BACKEND_TASKS.md` Part A fully (especially A.8, A.9), then do task T2. T0 is done. Only edit files owned by T2. Follow A.11.

**Goal:** turn facts into interpretations, with evidence, via declarative rules.

**Deliverables**
1. `engines/financial_snapshot.py`: `compute_snapshot(customer, events, now)` exactly per A.9. Handle no-income / no-spending edge cases without division by zero (spending floor €1 for ratios).
2. `rules/signals.py`:
   - `EVENT_SIGNAL_RULES`: list of `SignalEventRule`. Matching is generic (event type + equality/`in`/`ge` on data fields, keyword list for `KBC_SEARCH` queries, lower-cased). Examples: `TRANSACTION category=airline → AIR_TRAVEL_ACTIVITY 0.8`; `PAGE_VIEW page=electric_car_loan → ELECTRIC_CAR_LOAN_PAGE_VIEW 1.0`; `PAGE_VIEW page in [travel_insurance] → TRAVEL_PAGE_VIEW`; `PAGE_VIEW page=card_abroad_settings → FOREIGN_PAYMENT_SETTINGS_VIEWED`; `KBC_SEARCH keywords ["car","vehicle","ev"] + ["loan","financ","borrow"] → CAR_FINANCING_KBC_SEARCH`; `DECLARED_LIFE_EVENT expecting_child|child_born → PARENTHOOD_DECLARED`; `PRODUCT_OPENED child_savings_account → CHILD_ACCOUNT_OPENED`; `RECOMMENDATION_FEEDBACK` produces **no** signal (decision engine reads feedback events directly).
   - `PATTERN_THRESHOLDS` and `SIGNAL_TTL_DAYS` (default 60, per-type overrides).
3. `engines/signal_engine.py`: `SignalEngine.extract`, `detect_patterns` (one small generic function per pattern kind, parameterised by thresholds; pattern names mapped in a registry dict, not an if-chain), `extract_all` (drops expired signals, sorts by timestamp). Each signal gets a human `description` built from the event (e.g. "Airline payment of €420 at Brussels Airlines, 12 days ago"); **never** include the raw search query text in descriptions, use "KBC search about car financing".
4. `tests/test_financial_snapshot.py` and `tests/test_signal_engine.py`: each event rule; each pattern (positive and negative case); expiry; the brief's anti-example (one airline transaction yields a signal with strength < 1, never a moment); snapshot formulas incl. live transaction shifting `current_balance`; Lucas-like fixture: projected ≈ 1,787 then ≈ 287 after a live −€1,500.

**Acceptance:** tests green, no moment/intent logic in this code.

---

## T3: Generic scoring, Context Engine, Intent Engine

**Prompt:**
> You are agent T3 on the KBC Context backend. Read `BACKEND_TASKS.md` Part A fully (especially A.8, A.9), then do task T3. T0 is done. Only edit files owned by T3. Build your own Signal/Moment fixtures with the conftest builders; do not wait for T2. Follow A.11.

**Goal:** "what is happening" (moments with confidence + TTL) and "what do they want" (several intents), both explainable.

**Deliverables**
1. `engines/scoring.py`: one generic function, e.g. `weighted_sum(contributors: list[(ref, kind, weight, value, source_event_ids)], cap=1.0) -> (score, list[Evidence])`, used by both engines. Evidence contributions sum to the score (before the cap; if capped, scale or add a `rule` evidence "capped at 1.0").
2. `rules/moments.py`: `MOMENT_RULES` per A.9, plus `ACTIVE_THRESHOLD = 0.40`, `EMERGING_THRESHOLD = 0.20`.
3. `engines/context_engine.py`: for each rule: take signals inside the TTL window, strongest per type, weighted sum, `requires_any` cap (add a `rule` evidence explaining "Parenthood must be declared by the customer"), status, `detected_at`/`expires_at`, optional linear decay. Returns moments sorted by confidence.
4. `rules/intents.py`: `INTENT_RULES` per A.9 + `INTENT_MIN_CONFIDENCE = 0.10`.
5. `engines/intent_engine.py`: weighted sum from ACTIVE moments + signals + profile adjustments (generic dotted-path lookup on `CustomerProfile`), evidence per contributor, clamp, sorted.
6. `tests/test_context_engine.py`: car sequence (automotive only → 0.25 EMERGING; + page → 0.55 ACTIVE; + simulation → 0.85; + search → 1.0 capped); NEW_PARENT without declaration capped at 0.35 even with lots of baby expenses; TTL (a 40-day-old airline signal gives no TRAVEL); evidence contributions add up; empty signals → no moments.
7. `tests/test_intent_engine.py`: FIRST_SALARY 0.95 + LOW_EMERGENCY_BUFFER → BUILD_FINANCIAL_SAFETY ≥ 0.85, START_SAVING ≥ 0.70, START_INVESTING ≤ 0.40; multiple intents at once; EMERGING moments do not produce intents; forbidden `age` adjustment rejected by the rule schema; no rule references `age` (scan `INTENT_RULES`).

**Acceptance:** tests green; engines contain no moment/intent names.

---

## T4: Journeys, Decision Engine, Experience Builder

**Prompt:**
> You are agent T4 on the KBC Context backend. Read `BACKEND_TASKS.md` Part A fully (especially A.7, A.9), then do task T4. T0 is done. Only edit files owned by T4. Build your own Moment/Intent/Snapshot fixtures with the conftest builders; do not wait for T2/T3. Follow A.11.

**Goal:** the heart of the concept: decide what KBC should do **now**, including nothing, and turn it into frontend JSON.

**Deliverables**
1. `rules/journeys.py`: `JOURNEYS: dict[JourneyType, JourneyDef]` for the 8 journeys:
   - `FINANCIAL_FOUNDATION` (GUIDANCE): EMERGENCY_BUFFER_GOAL (INFO, calc emergency_buffer_goal), START_SAVINGS_PLAN (PRODUCT, no `product` field so it is never marked covered: it sets up a monthly transfer, payload from emergency_buffer_goal), BUDGET_OVERVIEW (SERVICE), LONG_TERM_PENSION_SAVINGS (PRODUCT pension_savings, calc monthly_for_target with target 100,000, horizon 40 years), LEARN_THE_BASICS (EDUCATION).
   - `FAMILY_START` (GUIDANCE): CHILD_LONG_TERM_SAVINGS (PRODUCT child_savings_account, target 20,000, 18 years), FAMILY_BUDGET_REVIEW (SERVICE), FAMILY_PROTECTION_CHECK (PRODUCT family_insurance), PARENTAL_BENEFITS_INFO (EDUCATION).
   - `RETIREMENT_TRANSITION` (GUIDANCE): INCOME_OVERVIEW (INFO), IDLE_CASH_INSIGHT (INFO, calc idle_cash_insight), PREPARE_ADVISOR_APPOINTMENT (APPOINTMENT), PLANNING_BASICS (EDUCATION).
   - `TRAVEL_READY` (GUIDANCE): CARD_ABROAD_CHECK (SETTINGS), TRAVEL_COVERAGE_STATUS (INFO), TRAVEL_INSURANCE (PRODUCT travel_insurance), TRAVEL_BUDGET (SERVICE), FOREIGN_PAYMENT_GUIDE (EDUCATION).
   - `CAR_PROJECT` (GUIDANCE): CAR_FINANCING_INFO (EDUCATION), CAR_LOAN_SIMULATION (SIMULATION, calc loan_monthly_payment on the latest simulated amount, default 25,000 / 60), CAR_INSURANCE_STATUS (PRODUCT car_insurance), BUDGET_IMPACT (INFO), SAVINGS_IMPACT (INFO). Eligibility monthly_income > 0.
   - `HOME_BUYING` (COMMERCIAL): MORTGAGE_SIMULATION, BORROWING_CAPACITY, DEPOSIT_SAVINGS, ADVISOR_APPOINTMENT.
   - `CASHFLOW_SUPPORT` (SUPPORT, urgent): CASHFLOW_FORECAST (INFO, calc cashflow_forecast), UPCOMING_PAYMENTS (SERVICE), SPENDING_PAUSE_TIPS (EDUCATION), TALK_TO_ADVISOR (APPOINTMENT).
   - `INVESTMENT_START` (COMMERCIAL): INVESTMENT_BASICS (EDUCATION), INVESTMENT_PLAN_SIMULATION (SIMULATION), RISK_PROFILE (SERVICE), INVESTMENT_PLAN (PRODUCT investment_plan). Eligibility emergency_buffer_months ≥ 1.
   - `serves_intents` mapping every intent of A.6 to at least one journey.
2. `rules/decisions.py`: weights, level thresholds, timing curve, suppression rule list, feedback windows (A.9).
3. `engines/calculators.py`: A.9 calculators, pure, with the Lucas/Julie/Marc check values.
4. `engines/decision_engine.py`: generic loop: build candidates from intents × journeys → compute breakdown → apply suppression rules in order (each rule a small function registered by id, parameters from rules) → rank → level/decision_type → `reasons` (short English sentences). Feedback is read from `RECOMMENDATION_FEEDBACK` events.
5. `rules/copy.py`: English templates keyed by moment/journey/decision type: hero titles and subtitles (e.g. FIRST_SALARY: "Your first salary just arrived" / "Let's build your financial foundation"; CASHFLOW: "Heads-up on your balance" / ...; CALM: "Everything looks on track." / "Nothing needs your attention today."; WAIT: calm hero + no journey), notice texts ("You're already covered for your trip."), why-sentences per evidence kind, `checks` labels for calm mode, disclaimer ("Amounts are illustrative simulations at 3% per year, not KBC rates or advice. Synthetic data.").
6. `engines/experience_builder.py`: mode from decision (PROACTIVE/SUGGESTION/PASSIVE/WAIT/CALM for NO_ACTION), hero from the primary journey's driving moment, journey cards with actions (status `ALREADY_COVERED` when owned, payloads from calculators), notices, `why` (top evidence, human text, no raw search queries), `checks` (always filled: buffer, cashflow, coverage, active moments, feedback), `under_the_hood` complete. Returns JSON only, no HTML.
7. Tests: `test_calculators.py` (check values), `test_decision_engine.py` (Lucas-like → FINANCIAL_FOUNDATION PROACTIVE; TRAVEL + owns travel_insurance → SHOW_SERVICE, insurance action ALREADY_COVERED, never SHOW_PRODUCT; START_INVESTING 0.9 + CASHFLOW_PRESSURE 0.95 → INVESTMENT_START suppressed CASHFLOW_RISK, CASHFLOW_SUPPORT primary SHOW_WARNING; NOT_RELEVANT feedback → FEEDBACK_DISMISSED; LATER → penalty only; nothing → NO_ACTION; only EMERGING moment → WAIT; score breakdown sums to total), `test_experience_builder.py` (CALM experience has hero "Everything looks on track." and checks; covered actions are marked; payload of Julie-like FAMILY_START has monthly 60 and progress 0.21; output serialises to JSON).

**Acceptance:** tests green; no persona names anywhere in `app/`.

---

## T5: API, service, security hardening

**Prompt:**
> You are agent T5 on the KBC Context backend. Read `BACKEND_TASKS.md` Part A fully (especially A.8, A.10), then do task T5. T0–T4 are done. Only edit files owned by T5. Follow A.11.

**Deliverables**
1. `services/personalization_service.py` (extend T0's file): `PersonalizationService(customer_repo, event_repo, clock, engines)` with `get_state(customer_id) -> PipelineResult` (cached per customer, invalidated on write), `add_event(customer_id, EventInput) -> PipelineResult` (the A.23 flow: validate, save, recompute, return), `add_feedback(...)`, `set_consent(...)`, `reset(customer_id)`, `apply_scenario_step(customer_id, scenario_id, step)`. Wire repositories from `seed_loader` at startup (lifespan).
2. `api/deps.py`: `get_service`, `resolve_customer` (single choke point, see A.10), `require_demo_mode`.
3. Endpoints (all JSON, `response_model` set):
   - `GET /customers` → list of `{id, first_name, age, headline}` (headline from profile, e.g. "Young professional, tenant").
   - `GET /customers/{id}` → customer (accounts, products, profile).
   - `GET /customers/{id}/overview` → the **generic, non-personalised** view: accounts, balances, recent transactions (last 10), and the same static generic banners for everyone ("Borrow for your projects", "Insure your home").
   - `GET /customers/{id}/context` → `CustomerContext`.
   - `GET /customers/{id}/intents` → `list[Intent]`.
   - `GET /customers/{id}/decision` → `Decision`.
   - `GET /customers/{id}/experience` → `PersonalizedExperience`.
   - `GET /customers/{id}/my-kbc` → everything the frontend needs: customer, profile, snapshot, moments, intents, decision, experience.
   - `POST /customers/{id}/events` (body `EventInput`) → new `my-kbc` payload.
   - `POST /customers/{id}/feedback` (body `{journey, feedback}`) → new `my-kbc` payload.
   - `PUT /customers/{id}/consent` (body `{personalization: bool}`) → new `my-kbc` payload.
   - `POST /customers/{id}/reset` (demo mode) → original state.
   - `GET /scenarios`, `POST /customers/{id}/scenarios/{scenario_id}/steps/{step}` (demo mode; scenario must belong to that customer or be customer-agnostic; step bounded).
   - `GET /health`.
4. `core/errors.py` + `main.py`: handlers (404 neutral, 422 without input echo, 500 generic), security headers middleware, CORS from settings, body size limit, OpenAPI tags and descriptions (judges will open `/docs`).
5. `tests/test_api.py`: every endpoint happy path; POST event recomputes (car scenario through the API step by step, confidence rises); reset restores; feedback changes the decision. `tests/test_security.py`: unknown/invalid ids → 404/422 without leaking; extra fields rejected; oversized body rejected; `days_ago` > 365 rejected; demo endpoints 403/404 when `KBC_DEMO_MODE=false`; no stack trace in 500 (force an error via dependency override); security headers present; one customer's events never appear in another's responses.

**Acceptance:** tests green; `uvicorn` runs; `/docs` readable.

---

## T6: End-to-end persona and scenario tests, rule tuning

**Prompt:**
> You are agent T6 on the KBC Context backend. Read `BACKEND_TASKS.md` Part A fully (especially A.4, A.9), then do task T6. T0–T4 are done. You own the e2e tests and, in this wave, you may tune **values** in `app/rules/*.py` (not engine code). Follow A.11.

**Goal:** prove the brief's section 26 with real seed data through `run_pipeline` (not through HTTP, so it runs in parallel with T5).

**Deliverables**
1. `tests/test_personas_e2e.py`: for each persona, load seed with the fixed `NOW`, run pipeline, assert every A.4 row (moment, confidence bounds, intents, primary journey, decision type, level, key payload numbers: Lucas €110 / 6%, Julie €60 / 21%, Marc 40,000 / 14,400 / 74%, Claire NO_ACTION + CALM + "Everything looks on track.").
2. `tests/test_scenarios_e2e.py`: each A.4 scenario step by step (apply events as `origin="live"`), asserting the expected table; plus: consent off → NO_ACTION with `NO_CONSENT`; NEW_PARENT never active for a clone of Julie without the declared event (baby expenses only); determinism (running twice gives identical JSON); **anti-hardcoding test**: clone Claire under a new id `test_clone` with Lucas's events → Lucas's outcome (proves the engine reacts to data, not ids); no persona name appears in `app/engines` or `app/rules` (grep in test).
3. Tune rule values if needed; list every changed value with before/after and why in your report (and update A.9 tables in this file accordingly, the only section of this file you may edit).

**Acceptance:** full `pytest -q` green.

---

## T7: README and docs for the judges

**Prompt:**
> You are agent T7 on the KBC Context backend. Read `BACKEND_TASKS.md` Part A fully, then do task T7. T0–T4 are done; T5 may still be running, so write API docs from the A.8/T5 spec and re-check them against the code at the end. Only edit files owned by T7. Follow A.11.

**Deliverables**
1. `backend/README.md` (judge-friendly, English): 1. idea (one paragraph + "the best recommendation is sometimes none"); 2. architecture diagram (ASCII) events → signals → context → intents → decision → journey → experience, with one concrete worked example (the electric car sequence with numbers); 3. install; 4. run; 5. tests; 6. endpoints table; 7. four personas and what each shows; 8. example event simulation with `curl` (car scenario, cashflow shock, feedback, reset); 9. explainability ("Why am I seeing this?" / "Under the hood"); 10. how it scales (pure per-customer pipeline, repository swap, event stream, rules as data); 11. security choices (A.10) and what production would add (auth session, persistence, audit log); 12. limitations (synthetic data, rules not learned, 3% illustrative, EUR only, floats for money, no LLM, scale argued not tested). Mention "Built for the KBC challenge at Tectonic Hackathon".
2. `docs/backend-architecture.md`: deeper design notes: rule tables (link to `app/rules`), scoring formula, suppression rules, TTL, how to add a new moment in 3 steps (add signal rule, moment rule, intent/journey mapping) without touching engine code.
3. `docs/api-examples.md`: request/response samples for `/my-kbc` (Lucas and Claire), `POST /events`, `POST /feedback` (generate them by running the app at the end, trimmed).
4. `backend/Dockerfile` (optional, small, non-root user, `uvicorn` on `$PORT`) for Cloud Run.
5. Update the root `README.md` to point to `backend/README.md`, and add a one-line note at the top of `KBC_Context_Tectonic_Hackathon.md`: "Superseded by KBC Context, see BACKEND_TASKS.md; personas and some figures are kept."

**Acceptance:** every command in the README runs as written.

---

# Part D: final acceptance checklist (run after wave 3)

- [ ] `cd backend && pytest -q` green, including e2e and security tests.
- [ ] `uvicorn app.main:app` starts; `/docs` lists all endpoints with descriptions.
- [ ] Lucas → FIRST_SALARY → FINANCIAL_FOUNDATION, €110 / 6%.
- [ ] Julie → NEW_PARENT (declared) → FAMILY_START, €60 / 21%.
- [ ] Marc → RETIREMENT_TRANSITION, €40,000 idle, advisor appointment.
- [ ] Claire → NO_ACTION, calm "Everything looks on track." with checks.
- [ ] Car scenario: 0.25 WAIT → 0.55 → 0.85 CAR_PROJECT journey, car insurance ALREADY_COVERED.
- [ ] Travel: covered customer gets reassurance, never a duplicate insurance.
- [ ] Cashflow shock: investing suppressed (CASHFLOW_RISK), CASHFLOW_SUPPORT primary.
- [ ] Feedback NOT_RELEVANT suppresses the journey; reset restores.
- [ ] `grep -riE "lucas|julie|marc|claire" backend/app/engines backend/app/rules` returns nothing.
- [ ] No secret, `.env` or key in git (`git log -p | grep -iE "key|secret|password"` reviewed).
- [ ] Every experience field needed by the frontend exists: hero, primary_journey, actions, notices, why, checks, under_the_hood, disclaimer.
