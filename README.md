# KBC Context: backend

**KBC Context is a FastAPI service that recomputes, on every request, what is happening in a customer's life from their profile and their event history (transactions, app pages, simulations, declared life events). From that it infers their life moments and probable needs, then decides what KBC should show them right now, including nothing, and explains every decision while respecting the customer's consent and feedback.**

Built for the KBC challenge at Tectonic Hackathon. The code lives in [backend/](backend/); design notes are in [backend/docs/](backend/docs/).

## 1. The idea

KBC Context is **not a product recommendation engine**. It is one generic, deterministic pipeline that works out what is happening in a customer's life from facts KBC already has. Those facts are transactions, KBC app pages, simulators, KBC search, owned products, declared life events and feedback. The pipeline then decides what KBC should do **right now**, and turns that decision into structured JSON the app renders. The same engine and the same rules run for every customer: different data gives a different experience. There is no `if customer_id == ...` anywhere.

> **The best recommendation is sometimes no recommendation.**
> A well-covered customer gets a calm "Everything looks on track." screen that lists what was checked. A customer under cash-flow pressure gets support, and product offers are paused.

All data is synthetic. KBC does not know which external websites a customer visits, so we only use signals that plausibly exist inside KBC.

## 2. Architecture

```
EVENTS        facts: transactions, KBC page views, simulations, KBC search, declared life events, feedback
  │           compute_snapshot()          balances, income, spending, projected balance, buffer, idle cash
  ▼
SIGNALS       interpretations with a strength (0..1), a TTL and the source event ids
  │           SignalEngine                25 event rules + 8 pattern detectors   (app/rules/signals.py)
  ▼
CONTEXT       Active Moments with a confidence and an expiry  ("what is happening?")
  │           ContextEngine               weighted sum of signals            (app/rules/moments.py)
  ▼
INTENTS       several probable needs at once  ("what do they want to achieve?")
  │           IntentEngine                moments + signals + profile nudges  (app/rules/intents.py)
  ▼
DECISION      score + suppression rules  ("what should KBC do now? maybe nothing")
  │           DecisionEngine                                                  (app/rules/decisions.py)
  ▼
JOURNEY       a reusable set of actions: info, simulation, product, service, appointment
  │                                                                           (app/rules/journeys.py)
  ▼
EXPERIENCE    JSON only: hero, journey cards, notices, "why", checks, under the hood, disclaimer
              ExperienceBuilder                                               (app/rules/copy.py)
```

Engines are pure: inputs in, outputs out, with the clock injected. All weights, thresholds and texts are data in [`backend/app/rules/`](backend/app/rules/). Paths in the diagram are relative to `backend/`.

### Worked example: the electric car (`electric_car` scenario, customer Claire)

`CAR_PROJECT` rule weights: automotive transaction 0.25, electric car loan page 0.30, loan simulation 0.30, KBC search 0.15.

| Step | New event | Signal added | `CAR_PROJECT` confidence | Decision |
|---|---|---|---|---|
| 1 | €500 deposit at an EV dealership | `AUTOMOTIVE_TRANSACTION` (1.0) | 0.25, `EMERGING` | `WAIT`: something may be starting, too early to act |
| 2 | Views the `electric_car_loan` page | `ELECTRIC_CAR_LOAN_PAGE_VIEW` | 0.55, `ACTIVE` | `CAR_PROJECT` journey, `SUGGESTION` (score 0.68) |
| 3 | Simulates €25,000 over 60 months | `ELECTRIC_CAR_LOAN_SIMULATION` | 0.85 | `CAR_PROJECT`, `PROACTIVE` (score 0.82) |
| 4 | KBC search "electric car loan" | `CAR_FINANCING_KBC_SEARCH` | 1.00 (capped) | `CAR_PROJECT`, `PROACTIVE` (score 0.86) |

Claire already owns car insurance, so the `CAR_INSURANCE_STATUS` action is marked `ALREADY_COVERED`, the decision is `SHOW_SERVICE` rather than a sale, and a notice says "Your car insurance is already in place." The loan payload shows €466.08/month at an illustrative 4.5%.

## 3. Install

Requires Python 3.12.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## 4. Run

All commands below run from `backend/`.

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: <http://localhost:8000/docs>. Configuration is read from environment variables only:

| Variable | Default | Meaning |
|---|---|---|
| `KBC_CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowed origins |
| `KBC_DEMO_MODE` | `true` | Enables `/reset` and the scenario endpoints |
| `KBC_MAX_BODY_BYTES` | `16384` | Request body size limit |
| `KBC_MAX_EVENTS_PER_CUSTOMER` | `2000` | Event log cap per customer |

Docker (Cloud Run friendly, listens on `$PORT`, default 8080):

```bash
docker build -t kbc-context .
docker run -p 8080:8080 kbc-context
```

## 5. Tests

```bash
pytest -q
```

The tests cover every engine, every rule table, the seed data, the calculators' check values, the personas and scenarios end to end, and the API and security behaviour. Tests use a fixed clock (`2026-10-01 09:00 UTC`), so results are deterministic.

## 6. Endpoints

All responses are JSON. `{id}` is a customer id such as `lucas`.

| Method | Path | Returns |
|---|---|---|
| `GET` | `/health` | `{"status": "ok"}` |
| `GET` | `/customers` | Demo customers: `id`, `first_name`, `age`, `headline` |
| `GET` | `/customers/{id}` | Customer: profile, accounts, products |
| `GET` | `/customers/{id}/overview` | The **generic, non-personalised** view: accounts, last 10 transactions, the same static banners for everyone (the "before") |
| `GET` | `/customers/{id}/context` | `CustomerContext`: profile, products, snapshot, signals, moments |
| `GET` | `/customers/{id}/intents` | `list[Intent]` |
| `GET` | `/customers/{id}/decision` | `Decision` |
| `GET` | `/customers/{id}/experience` | `PersonalizedExperience` |
| `GET` | `/customers/{id}/my-kbc` | Everything the frontend needs: customer, profile, snapshot, moments, intents, decision, experience (the "after") |
| `POST` | `/customers/{id}/events` | Adds one event (body `EventInput`), recomputes, returns the new `my-kbc` payload |
| `POST` | `/customers/{id}/feedback` | Body `{journey, feedback}` with `NOT_RELEVANT`, `LATER` or `USEFUL`; returns the new `my-kbc` payload |
| `PUT` | `/customers/{id}/consent` | Body `{personalization: bool}`; returns the new `my-kbc` payload |
| `POST` | `/customers/{id}/reset` | Demo mode only. Restores the seed state |
| `GET` | `/scenarios` | Demo mode only. The 5 demo scenarios |
| `POST` | `/customers/{id}/scenarios/{scenario_id}/steps/{step}` | Demo mode only. Applies one scenario step (1-based) |

Full request and response samples: [backend/docs/api-examples.md](backend/docs/api-examples.md).

## 7. The four personas

| Id | Who | What the engine finds | What it shows |
|---|---|---|---|
| `lucas` | 24, first salary, tenant, low savings | `FIRST_SALARY` 0.95 | `FINANCIAL_FOUNDATION`, `PROACTIVE`: a 3-month safety cushion, then **€110/month** toward €100,000 of pension savings ("without changing anything: **6%** of the goal") |
| `julie` | 31, has **declared** she is expecting a child | `NEW_PARENT` 0.89 | `FAMILY_START`: **€60/month** to reach €20,000 by the child's 18th birthday ("without changing anything: **21%**") |
| `marc` | 66, salary stopped, pension started | `RETIREMENT_TRANSITION` 0.90 | `RETIREMENT_TRANSITION`: **€40,000 idle** above a €14,400 cushion (**74%** of liquid money inactive), with "Prepare an advisor appointment" as next step |
| `claire` | 38, well covered: 10 products, 6.3 months of buffer | nothing | `NO_ACTION`, mode `CALM`: "Everything looks on track." with the 5 checks that led there |

Parenthood is never inferred from spending. Without Julie's declaration, `NEW_PARENT` is capped at 0.35 whatever the baby purchases. No rule uses `age`.

## 8. Simulating events with `curl`

Start the API, then:

```bash
# Electric car, step by step (Claire): WAIT -> SUGGESTION -> PROACTIVE, car insurance ALREADY_COVERED
curl -s -X POST localhost:8000/customers/claire/scenarios/electric_car/steps/1
curl -s -X POST localhost:8000/customers/claire/scenarios/electric_car/steps/2
curl -s -X POST localhost:8000/customers/claire/scenarios/electric_car/steps/3
curl -s -X POST localhost:8000/customers/claire/reset

# A raw event: a simulation on its own only reaches 0.30, so the answer is WAIT
curl -s -X POST localhost:8000/customers/claire/events \
  -H 'Content-Type: application/json' \
  -d '{"type": "SIMULATION", "data": {"simulation_type": "electric_car_loan", "amount": 25000, "duration_months": 60}}'
curl -s -X POST localhost:8000/customers/claire/reset

# Cash-flow shock (Lucas): explores investing, then an unexpected €1,500 garage bill
curl -s -X POST localhost:8000/customers/lucas/scenarios/cashflow_shock/steps/1
curl -s -X POST localhost:8000/customers/lucas/events \
  -H 'Content-Type: application/json' \
  -d '{"type": "TRANSACTION", "data": {"direction": "out", "amount": 1500, "category": "unexpected_expense", "merchant": "Garage Dupont"}}'
curl -s -X POST localhost:8000/customers/lucas/reset

# Feedback: "not relevant" suppresses the journey for 30 days
curl -s -X POST localhost:8000/customers/lucas/feedback \
  -H 'Content-Type: application/json' \
  -d '{"journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT"}'
curl -s -X POST localhost:8000/customers/lucas/reset
```

Add `| python3 -m json.tool` to pretty-print. What each step shows:

- **Cash-flow shock**: after step 1, `START_INVESTING` is 0.86 and `INVESTMENT_START` appears as a secondary journey. After the garage bill, the projected balance drops from about €1,787 to €287. `CASHFLOW_PRESSURE` becomes active (1.00), `CASHFLOW_SUPPORT` becomes primary (`SHOW_WARNING`), and `INVESTMENT_START` is suppressed with rule `CASHFLOW_RISK`.
- **Feedback**: `FINANCIAL_FOUNDATION` is suppressed with rule `FEEDBACK_DISMISSED`. Nothing else is relevant enough, so the screen goes `CALM`.
- **Reset** restores the seed state for that customer.

## 9. Explainability

Every inference keeps its evidence: which signal, moment, profile field or rule contributed, and how much. The contributions add up to the score.

- **"Why am I seeing this?"**: `experience.why` lists the top contributors in plain English, for example "Your first regular salary arrived" (+0.70).
- **"What we checked"**: `experience.checks` is always filled: safety cushion, balance until next income, protection, life moments, feedback. That is how the calm screen proves the engine looked and chose to stay quiet.
- **"Under the hood"**: `experience.under_the_hood` holds the whole chain: profile, products, snapshot, signals with source event ids, moments with expiry, intents, the decision with its score breakdown and weights, and every suppressed candidate with its rule and reason.
- Raw KBC search queries are never echoed. They appear as "KBC search about car financing".

## 10. How it scales

- **Pure per-customer pipeline.** State is recomputed from the customer's profile, event log and `now`. There is no shared state between customers, so processing can be partitioned by customer id.
- **Repository swap.** Storage sits behind `CustomerRepository` and `EventRepository` interfaces. The in-memory implementation can be replaced by a database without touching the engines.
- **Event stream.** In production, the same engines would consume an event stream (transactions, app telemetry) and update each customer's context incrementally instead of on every read.
- **Rules as data.** A new life moment is new rule data, not new engine code. See [backend/docs/backend-architecture.md](backend/docs/backend-architecture.md#adding-a-new-moment).

## 11. Security choices

- Every input is validated by Pydantic: unknown fields rejected, bounded numbers and strings, enums instead of free text. Search queries are stripped, limited to 100 characters, control characters rejected, never logged.
- `customer_id` goes through a single dependency, `resolve_customer`: pattern check, then repository lookup, and 404 with a neutral message if unknown. In this demo the id is in the path. **In production it comes from the authenticated session, never the path (IDOR).** `resolve_customer` is the one place to change.
- The server sets event `id`, `timestamp` and `origin`. Client timestamps are never trusted. `days_ago` is demo-only and capped at 365.
- Errors return `{"error": {"code", "message"}}`, with no stack trace, and 422 responses do not echo input values.
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`. CORS comes from configuration.
- The request body is limited to 16 KB and each customer's event log to 2,000 events.
- No secrets, no `.env` in git, no `pickle`, `eval` or `yaml.load`. Seed files are read from fixed paths inside the package.

What production would add: real authentication and session handling, persistent storage, an audit log of decisions and consent changes, rate limiting, and encryption at rest.

## 12. Limitations

- **Synthetic data**: four personas and five scenarios, built by hand.
- **Rules are not learned**: weights and thresholds are hand-tuned. Feedback events could later train them.
- **Illustrative amounts**: 3% per year for savings and 4.5% for loans. These are not KBC rates or advice, and the experience says so.
- **EUR only**, and money is stored as `float` rounded to 2 decimals (a PoC shortcut; production would use `Decimal`).
- **No LLM** in the decision path, by design: the output is deterministic and explainable.
- **Scale is argued, not tested**: no load test was run.
