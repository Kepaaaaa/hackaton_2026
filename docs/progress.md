# Backend progress

Task split: [BACKEND_TASKS.md](../BACKEND_TASKS.md).

## T0: Foundation ✅

T0 builds the project skeleton so T1 to T4 can work in parallel on stable types.

- **Project**: `backend/` (Python 3.12, FastAPI, Pydantic v2, pytest). No database.
- **Data models** (`app/models/`): every shared type is defined once and frozen: customer, event, signal, snapshot, moment, intent, decision, experience.
  - Every input is validated: unknown fields, invalid amounts and unknown pages are rejected, and searches are capped at 100 characters.
- **Rule schema** (`app/rules/schema.py`): the format of the rules. Rules are data, not code. `age` is forbidden as a rule input.
- **Pipeline** (`app/services/personalization_service.py`): `run_pipeline` chains the steps events → signals → moments → intents → decision → experience. If the customer has not given consent, the result is `NO_ACTION`.
- **Utilities**: injectable clock (deterministic tests), config via `KBC_*` env vars, thread-safe in-memory storage.
- **Stubs**: every file owned by T1 to T7 exists. Engines have their final signatures and are still empty.
- **API**: `GET /health` only.
- **Tests**: 44 green, with shared builders in `tests/conftest.py`.

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" && pytest -q
```

**Next**: T1 (data), T2 (signals), T3 (moments/intents) and T4 (decision/experience), in parallel.

## T3: Scoring, Context Engine, Intent Engine ✅

- **Scoring** (`engines/scoring.py`): `weighted_sum` is shared by both engines. Each contributor becomes one piece of evidence, and the contributions always add up to the score (when a score is capped, a `rule` evidence line records the cut).
- **Moments** (`rules/moments.py`, `engines/context_engine.py`): signals → moments with the A.9 weights. Only signals inside the TTL window count, one per type (the strongest). A moment is `ACTIVE` from 0.40 and `EMERGING` from 0.20. `NEW_PARENT` is capped at 0.35 unless parenthood is declared.
- **Intents** (`rules/intents.py`, `engines/intent_engine.py`): combines ACTIVE moments, signals and profile adjustments into several intents at once, drops anything under 0.10. A profile adjustment on its own never creates an intent. `age` is never used.
- **Tests**: 38 new, covering the car sequence, the parenthood cap, TTL, Lucas-style numbers, and checks that engines contain no moment or intent names.
- **Deviation**: the explanation text for capped moments lives in `rules/moments.py` (`REQUIRED_SIGNAL_EXPLANATIONS`), not in `schema.py`, to avoid editing a T0 file.

## T2: Snapshot + Signals ✅

T2 turns raw facts into interpretations.

- **Snapshot** (`engines/financial_snapshot.py`): balances, income, spending, projected balance, buffer, idle cash, debt, exactly per A.9. No division by zero.
- **Rules** (`rules/signals.py`): 25 declarative event → signal rules (strength, TTL, description template).
- **Engine** (`engines/signal_engine.py`): generic rule matching + 8 pattern detectors in a registry. Expired signals dropped. Search queries never appear in descriptions.
- **Tests**: 173 green (Lucas: projected ≈ €1,787, ≈ €287 after the −€1,500 shock).

## T1: Personas, seed history, scenarios ✅

- **Customers** (`app/data/customers.json`): Lucas, Julie, Marc, Claire with profiles, accounts and products per A.4.
- **History** (`app/data/events.json`): ~115–150 events per customer over ~180 days, in relative time (`days_ago`, `hour`), with realistic noise. Amounts are calibrated to land exactly on the A.9 figures.
- **Scenarios** (`app/data/scenarios.json`): the 5 A.4 demo scenarios.
- **Loader** (`repositories/seed_loader.py`): `load_seed(now)` validates everything and assigns ids `evt_<customer>_0001`; `scenario_step_events(id, step)` uses a **0-based** step.
- **Tests**: 17 (validity, persona facts, snapshot hand-computed).

| | spending/month | buffer | projected | idle |
|---|---|---|---|---|
| Lucas | 1,600 | 2.17 mo | 1,787 (→ 287 after shock) | 0 |
| Julie | 2,500 | 1.12 mo | 2,567 | 0 |
| Marc | 2,400 | 21.7 mo | 52,800 | 40,000 (74%) |
| Claire | 3,000 | 6.33 mo | 3,500 | 4,000 (18%) |

**Note for T6**: Julie's buffer < 3 → `FIRST_SALARY` ≈ 0.25 (EMERGING) from `LOW_EMERGENCY_BUFFER` + `SALARY_RECEIVED`.

## T4: Journeys, decision, experience ✅

- **Journeys** (`rules/journeys.py`): the 8 journeys with their actions. Every intent is served by at least one journey.
- **Decision** (`engines/decision_engine.py` + `rules/decisions.py`): score = intent + timing + usefulness + eligibility + financial fit − penalties, then 6 suppression rules in order (NO_CONSENT, LOW_CONFIDENCE, FEEDBACK_DISMISSED, CASHFLOW_RISK, ALREADY_COVERED, NOT_ELIGIBLE). Result: a journey, or `WAIT`, or `NO_ACTION`.
- **Calculators** (`engines/calculators.py`): savings goal, idle cash, safety cushion, loan, cash flow. Illustrative 3%.
- **Experience** (`engines/experience_builder.py` + `rules/copy.py`): JSON with hero, journey cards (owned products → `ALREADY_COVERED`), notices, why, 5 checks, under the hood, disclaimer.
- **Tests**: 40 new, 213 green in total.

Checked on real seed data: Lucas €110 / 6%, Julie €60 / 21%, Marc €40,000 idle / 74%, Claire CALM. All 5 scenarios behave as in A.4.

**Note for T5**: `ExperienceBuilder.build` takes an optional `events=` argument (to use the simulated loan amount). `run_pipeline` should pass it; without it the default €25,000 / 60 months is used.

## T6: End-to-end tests ✅

- **Tests** (`test_personas_e2e.py`, `test_scenarios_e2e.py`): 33 tests. They run the real seed data through `run_pipeline` and check every A.4 row and scenario, plus: no consent, parenthood never inferred, determinism, clone under a new id, no persona names in engines/rules.
- **Rule tuning**: none. Every expected value was already reached.
- **Julie FIRST_SALARY 0.25**: left as it is. It stays EMERGING and never reaches the decision (a test checks this). Tuning it would break T3's unit tests.

**Note for T5**: `test_foundation.py` has 2 failures because `run_pipeline` now passes `events=` and T0's `_FakeExperience.build` does not accept it.

## T7: Docs for the judges ✅

- **`backend/README.md`**: idea, pipeline diagram, electric car example with numbers, install/run/tests, endpoints, the 4 personas, `curl` demo, explainability, scale, security, limitations.
- **`docs/backend-architecture.md`**: formulas, suppression rules, TTL, adding a moment without touching the engines.
- **`docs/api-examples.md`**: trimmed JSON from the real pipeline (Lucas, Claire, cash-flow shock, feedback, errors).
- **`backend/Dockerfile`**: non-root, `$PORT` (Cloud Run). Built and tested: `/health` OK.
- Root `README.md` points to the backend. Superseded note added to `KBC_Context_Tectonic_Hackathon.md`.
- **Checked**: every `curl` in the README was run against the live API and gives the documented result.

**Note for T5**: the scenario endpoint uses a **1-based** step (the docs follow this). `test_foundation.py` has 2 failures because `run_pipeline` now passes `events=` to a fake `ExperienceBuilder` in the test.

## T5: API, service, security ✅

- **Service** (`services/personalization_service.py`): `PersonalizationService` runs the pipeline once per customer and caches the result. Any write clears that customer's cache. It covers events, feedback, consent, reset and scenario steps. The server sets event ids (`evt_<id>_live_0001`), the timestamp and `origin="live"`. `run_pipeline` now passes the events to the experience builder, so the car loan uses the amount that was actually simulated.
- **API** (`api/*`, `main.py`): every A.8/T5 endpoint (`/customers`, `/overview`, `/context`, `/intents`, `/decision`, `/experience`, `/my-kbc`, `POST /events`, `/feedback`, `PUT /consent`, `/reset`, `/scenarios`, scenario steps). Scenario steps in the URL start at **1**. `create_app(settings, service)` lets tests inject their own setup. `/docs` has tags and descriptions.
- **Security**:
  - `resolve_customer` is the only place that checks a customer id; an invalid or unknown id gets the same neutral 404.
  - Every error uses `{"error": {code, message}}`. 422 responses never repeat what the client sent (Pydantic messages that quote it are masked), and a 500 never shows a stack trace.
  - Security headers, plus `no-store` on customer data. CORS allows only the origins in `KBC_CORS_ORIGINS`.
  - Bodies over 16 KB get 413, even without a Content-Length header. Each customer's event log stops at 2,000 events (429).
  - With `KBC_DEMO_MODE=false`, the demo endpoints return 404.
- **Tests**: `test_api.py` and `test_security.py`, 114 new tests; 327 pass in total.
- **Deviation**: I added `events=()` to the fake builder in `tests/test_foundation.py` (T0) so it accepts the new `events=` argument.

## Final check ✅

Every item of the Part D checklist was checked against the live API (all personas, all 5 scenarios, feedback and reset, neutral 404, `/docs`, no persona names in engines/rules, no secrets in git).

- **Wording**: decision reasons say "today", "yesterday" or "N days ago" instead of "0 day(s) ago" (`_days_ago` in `engines/decision_engine.py`, same style as the signal descriptions). New test in `test_decision_engine.py`.
- **Test warning**: `httpx2` added to the dev dependencies, which Starlette ≥ 1.x now expects for `TestClient`. `httpx` stays for older Starlette versions.
- **Note for the frontend**: in the electric car scenario the decision is `SHOW_SERVICE`, not `SHOW_JOURNEY`, because the only product (car insurance) is already owned (rule in A.9). The journey card is still there in `primary_journey`.
- **Tests**: 330 green, no warnings.
