# KBC Context: backend architecture

Design notes behind the [README](../../README.md).

## Principles

1. **Events are facts, signals are interpretations.** One event never becomes an intent directly.
2. **Rules are data.** Every weight, threshold, TTL, journey and text lives in `backend/app/rules/`. Engines are generic loops over those rules and never name a moment, intent or journey in an `if`.
3. **Pure and deterministic.** Each engine takes inputs and returns outputs. The clock is injected. There is no I/O, no global state and no LLM. The same profile, events and `now` always give the same JSON.
4. **Evidence everywhere.** Every signal, moment, intent and score carries the contributions that produced it.
5. **Sensitive moments are declared.** Parenthood needs a customer declaration (or an opened child account). `age` is rejected by the rule schema.

## Pipeline

`run_pipeline(customer, events, now)` in `app/services/personalization_service.py`:

| Step | Code | Rules |
|---|---|---|
| Snapshot | `engines/financial_snapshot.py` | formulas in A.9 |
| Signals | `engines/signal_engine.py` | [`rules/signals.py`](../app/rules/signals.py) |
| Moments | `engines/context_engine.py` | [`rules/moments.py`](../app/rules/moments.py) |
| Intents | `engines/intent_engine.py` | [`rules/intents.py`](../app/rules/intents.py) |
| Decision | `engines/decision_engine.py` | [`rules/decisions.py`](../app/rules/decisions.py), [`rules/journeys.py`](../app/rules/journeys.py) |
| Experience | `engines/experience_builder.py`, `engines/calculators.py` | [`rules/copy.py`](../app/rules/copy.py) |

The rule formats themselves (`SignalEventRule`, `MomentRule`, `IntentRule`, `Condition`, `SuppressionRule`...) are Pydantic models in [`rules/schema.py`](../app/rules/schema.py), so a malformed rule fails at import time.

If the customer has turned personalization off, the pipeline stops after the snapshot and returns `NO_ACTION` with reason `NO_CONSENT`.

## Signals

- **Event rules** (25): an event type plus field matches (`eq`, `in`, `ge`, or keyword lists for KBC search) produce one signal with a strength and a description template. Example: an `airline` debit gives `AIR_TRAVEL_ACTIVITY` at strength 0.8, because a flight alone is ambiguous (it could be a gift).
- **Pattern detectors** (8): look at history and the snapshot, for example `FIRST_RECURRING_SALARY` (salary in the last 30 days, none in the 180 days before), `LOW_PROJECTED_BALANCE` or `HIGH_IDLE_CASH`. Their thresholds are in `PATTERN_THRESHOLDS`, and the detectors are registered in a dict (`PATTERN_DETECTORS`), not an if-chain.
- **TTL**: 60 days by default, overridable per signal type (`SIGNAL_TTL_DAYS`). Expired signals are dropped.
- Raw KBC search text never appears in a description.

## Moments and TTL

```
confidence = min(1, Σ weight(signal type) × strongest strength of that type)
```

- Only signals inside the moment's window (`ttl_days` before `now`) count, and each signal type counts once.
- `ACTIVE` from 0.40, `EMERGING` from 0.20, not returned below 0.20.
- `requires_any` + `cap_without_required`: `NEW_PARENT` stays at or below 0.35 unless `PARENTHOOD_DECLARED` or `CHILD_ACCOUNT_OPENED` is present. A `rule` evidence line explains the cap.
- `detected_at` is the earliest contributing signal and `expires_at` is the latest one plus the TTL. So a trip is forgotten 30 days after the last travel signal, while a first salary stays relevant for 90 days.

## Intents

```
confidence = clamp(Σ w × ACTIVE moment confidence + Σ w × signal strength + profile adjustments, 0, 1)
```

- One context produces several intents. Lucas, for example, gets `BUILD_FINANCIAL_SAFETY` 0.96, `START_SAVING` 0.81, `LEARN_BUDGETING` 0.57 and `START_INVESTING` 0.14.
- `EMERGING` moments do not feed intents.
- Profile adjustments are `(path, equals, delta)` nudges on the composable profile (for example `financial_maturity = beginner`). They never create an intent on their own. Intents below 0.10 are dropped.

## Decision scoring

Candidates are intents × journeys. For each journey J, `intent_confidence = max(intent.confidence × J.serves_intents[intent])`.

```
score = 0.35 × intent_confidence
      + 0.25 × timing_relevance     1.0 while moment age ≤ 33% of its TTL, then linear down to 0.3
      + 0.20 × usefulness           J.usefulness × (1 − 0.5 × share of J's products already owned)
      + 0.10 × eligibility          1 if every J.eligibility condition holds
      + 0.10 × financial_fit        safety = 0.6 × clamp(projected / spending) + 0.4 × clamp(buffer / 6)
                                    SUPPORT journeys use 1 − safety
      − penalties                   LATER feedback in the last 7 days: 0.25
```

The `ScoreBreakdown` in every candidate holds each term and the weights, and the terms add up to `total`.

### Suppression rules

Evaluated in order. The first rule that matches suppresses the candidate, and the decision records it in `suppressed` with a human reason.

| Rule | When | Effect |
|---|---|---|
| `NO_CONSENT` | personalization turned off | everything, `NO_ACTION` |
| `LOW_CONFIDENCE` | `intent_confidence` < 0.40 | candidate dropped |
| `FEEDBACK_DISMISSED` | `NOT_RELEVANT` on this journey in the last 30 days | suppressed |
| `CASHFLOW_RISK` | `CASHFLOW_PRESSURE` ≥ 0.70 or low projected balance | every `COMMERCIAL` journey suppressed; `SUPPORT` and `GUIDANCE` stay |
| `ALREADY_COVERED` | every product action owned and no other action | suppressed; otherwise owned actions are marked `ALREADY_COVERED` and a reassurance notice is added |
| `NOT_ELIGIBLE` | an eligibility condition fails (for example `INVESTMENT_START` needs a buffer of at least 1 month) | suppressed |

### Choosing

- Best remaining score ≥ 0.80 → `PROACTIVE`, 0.60 to 0.80 → `SUGGESTION`, 0.40 to 0.60 → `PASSIVE` (`PASSIVE_PERSONALIZATION`). Up to 2 secondary journeys with a score of 0.40 or more.
- No candidate reaches 0.40: `WAIT` if a moment is `EMERGING` (or the best option is not timely), else `NO_ACTION`.
- Decision type by journey kind: `SUPPORT` gives `SHOW_WARNING` when urgent and `SHOW_GUIDANCE` otherwise; `GUIDANCE` and `COMMERCIAL` give `SHOW_JOURNEY`. If every product action is already owned, the type is `SHOW_SERVICE`.

## Experience

`ExperienceBuilder` turns the decision into JSON. It never produces HTML.

- `mode`: `PROACTIVE`, `SUGGESTION`, `PASSIVE`, `WAIT`, or `CALM` (for `NO_ACTION`).
- `hero`: title, subtitle and tone from the moment behind the primary journey (texts in `rules/copy.py`).
- Journey cards with actions. Payloads come from `engines/calculators.py`: savings goal, idle cash, safety cushion, loan, cash-flow forecast. The rates (3% savings, 4.5% loans) are illustrative.
- `notices`, `why` (top evidence in plain English), `checks` (always 5 items), `under_the_hood` (the full chain) and `disclaimer`.

## Adding a new moment

Example: a `STUDENT_GRADUATION` moment. No engine code changes.

1. **Vocabulary.** Add the new members to the enums in `app/models/common.py` (`SignalType`, `MomentType`, and `IntentType` / `JourneyType` if needed). Adding members is allowed; renaming or removing is not.
2. **Signal rule.** In `rules/signals.py`, add a `SignalEventRule`, for example a `PAGE_VIEW` of a new page giving `GRADUATION_PAGE_VIEW` at strength 1.0, with a description template.
3. **Moment and intent/journey mapping.**
   - In `rules/moments.py`, add a `MomentRule` with signal weights and `ttl_days`.
   - In `rules/intents.py`, add or extend an `IntentRule` with `moment_weights` for the new moment.
   - In `rules/journeys.py`, map the intent in a journey's `serves_intents`, or add a `JourneyDef` with its actions.
   - In `rules/copy.py`, add the hero text and the "why" sentence for the new signal.

The engines pick up the new rules on the next run. The only case that needs code is a new **pattern** over history: that means one new detector function registered in `PATTERN_DETECTORS`, with its thresholds in `rules/signals.py`.

## Storage and scale

- `CustomerRepository` and `EventRepository` (`app/repositories/base.py`) are protocols. The in-memory implementation is thread-safe, returns deep copies and caps each customer's event log.
- The seed (`app/data/*.json`) uses relative time (`days_ago`), so the demo never goes stale.
- State is a pure function of one customer's data, so processing is partitionable by customer id. A production version would run the same engines on an event stream and cache the result per customer.
