# KBC Context: API examples

Request and response samples for the main endpoints. The endpoint list is in [README.md](../../README.md#6-endpoints), and the live schema is at `/docs` when the API runs.

The values come from the real pipeline on the seed data, with the clock at `2026-10-01T09:00:00Z`. Responses are **trimmed**: `…` marks removed fields, and `under_the_hood` is omitted (it repeats the full chain: profile, products, snapshot, signals, moments, intents, decision).

Every `my-kbc` payload has the same top-level keys:

```json
{ "customer": {…}, "profile": {…}, "snapshot": {…}, "moments": […], "intents": […], "decision": {…}, "experience": {…} }
```

## `GET /customers/lucas/my-kbc`

First salary, low buffer. Result: `FINANCIAL_FOUNDATION`, `PROACTIVE`.

```json
{
  "snapshot": {
    "current_balance": 3280.0, "savings_balance": 1800.0, "liquid_balance": 5080.0,
    "monthly_income": 2450.0, "income_sources": ["salary"], "avg_monthly_spending": 1600.0,
    "next_income_date": "2026-10-29", "days_until_next_income": 28,
    "projected_balance_before_next_income": 1786.67, "emergency_buffer_months": 2.175,
    "idle_cash": 0.0, "idle_ratio": 0.0, "monthly_margin": 850.0, "…": "…"
  },
  "moments": [
    { "type": "FIRST_SALARY", "confidence": 0.95, "status": "ACTIVE", "expires_at": "2026-12-30T09:00:00Z", "evidence": ["…"] }
  ],
  "intents": [
    { "type": "BUILD_FINANCIAL_SAFETY", "confidence": 0.9625, "…": "…" },
    { "type": "START_SAVING", "confidence": 0.815, "…": "…" },
    { "type": "LEARN_BUDGETING", "confidence": 0.575, "…": "…" },
    { "type": "START_INVESTING", "confidence": 0.14, "…": "…" }
  ],
  "decision": {
    "decision_type": "SHOW_JOURNEY",
    "level": "PROACTIVE",
    "primary": {
      "journey": "FINANCIAL_FOUNDATION",
      "score": 0.9314,
      "breakdown": {
        "intent_confidence": 0.9625, "timing_relevance": 1.0, "usefulness": 0.85,
        "eligibility": 1.0, "financial_fit": 0.745, "penalties": 0.0,
        "weights": { "intent_confidence": 0.35, "timing_relevance": 0.25, "usefulness": 0.2, "eligibility": 0.1, "financial_fit": 0.1 },
        "total": 0.9314
      },
      "…": "…"
    },
    "suppressed": [
      { "journey": "INVESTMENT_START", "rule": "LOW_CONFIDENCE", "reason": "Intent confidence 0.14 is below 0.40.", "score_before": 0.6335 }
    ],
    "reasons": [
      "FINANCIAL_FOUNDATION selected with score 0.93 (PROACTIVE).",
      "Driven by BUILD_FINANCIAL_SAFETY (relevance-weighted confidence 96%)."
    ]
  },
  "experience": {
    "customer_id": "lucas",
    "mode": "PROACTIVE",
    "hero": { "type": "FIRST_SALARY", "title": "Your first salary just arrived", "subtitle": "Let's build your financial foundation", "tone": "positive" },
    "primary_journey": {
      "type": "FINANCIAL_FOUNDATION",
      "title": "Build your financial foundation",
      "priority": 0.9314,
      "decision_type": "SHOW_JOURNEY",
      "actions": [
        { "id": "EMERGENCY_BUFFER_GOAL", "kind": "INFO", "label": "Set your safety cushion goal", "status": "AVAILABLE",
          "payload": { "target_months": 3, "target": 4800.0, "current": 1800.0, "gap": 3000.0, "suggested_monthly": 250, "months_to_goal": 12 } },
        { "id": "START_SAVINGS_PLAN", "kind": "PRODUCT", "label": "Start a monthly savings transfer", "status": "AVAILABLE", "payload": { "…": "same as above" } },
        { "id": "BUDGET_OVERVIEW", "kind": "SERVICE", "label": "See where your money goes", "status": "AVAILABLE", "payload": {} },
        { "id": "LONG_TERM_PENSION_SAVINGS", "kind": "PRODUCT", "label": "Think long term: pension savings", "status": "AVAILABLE",
          "payload": { "monthly": 110, "current": 1800.0, "target": 100000.0, "months": 480, "annual_rate": 0.03, "progress_without_change": 0.06, "capped": false, "horizon_years": 40 } },
        { "id": "LEARN_THE_BASICS", "kind": "EDUCATION", "label": "Money basics in 5 minutes", "status": "AVAILABLE", "payload": {} }
      ]
    },
    "secondary_journeys": [],
    "notices": [],
    "why": [
      { "text": "Your first regular salary arrived", "contribution": 0.7 },
      { "text": "A salary was paid into your account", "contribution": 0.15 },
      { "text": "Your savings cover less than 3 months of expenses", "contribution": 0.1 }
    ],
    "checks": [
      { "label": "Safety cushion", "ok": false, "detail": "2.2 months of expenses set aside" },
      { "label": "Balance until next income", "ok": true, "detail": "About €1,787 expected before your next income" },
      { "label": "Protection", "ok": false, "detail": "Something relevant is not covered yet" },
      { "label": "Life moments", "ok": false, "detail": "Detected: FIRST_SALARY" },
      { "label": "Your feedback", "ok": true, "detail": "No suggestion was dismissed" }
    ],
    "generated_at": "2026-10-01T09:00:00Z",
    "disclaimer": "Amounts are illustrative simulations at 3% per year, not KBC rates or advice. Synthetic data."
  }
}
```

## `GET /customers/claire/my-kbc`

Well covered, nothing happening. Result: `NO_ACTION`, calm mode.

```json
{
  "snapshot": {
    "current_balance": 4000.0, "savings_balance": 18000.0, "monthly_income": 3900.0,
    "avg_monthly_spending": 3000.0, "projected_balance_before_next_income": 3500.0,
    "emergency_buffer_months": 6.3333, "idle_cash": 4000.0, "idle_ratio": 0.1818, "…": "…"
  },
  "moments": [],
  "intents": [],
  "decision": {
    "decision_type": "NO_ACTION",
    "level": "NONE",
    "primary": null,
    "secondary": [],
    "suppressed": [],
    "reasons": ["No journey is relevant enough right now (best score below 0.40). Nothing to show."],
    "…": "…"
  },
  "experience": {
    "customer_id": "claire",
    "mode": "CALM",
    "hero": { "type": "CALM", "title": "Everything looks on track.", "subtitle": "Nothing needs your attention today.", "tone": "calm" },
    "primary_journey": null,
    "secondary_journeys": [],
    "notices": [],
    "why": [{ "text": "No life moment currently needs your attention", "contribution": 0.0 }],
    "checks": [
      { "label": "Safety cushion", "ok": true, "detail": "6.3 months of expenses set aside" },
      { "label": "Balance until next income", "ok": true, "detail": "About €3,500 expected before your next income" },
      { "label": "Protection", "ok": true, "detail": "4 protection product(s) in place, nothing missing for what's happening now" },
      { "label": "Life moments", "ok": true, "detail": "No life moment needs attention" },
      { "label": "Your feedback", "ok": true, "detail": "No suggestion was dismissed" }
    ],
    "disclaimer": "Amounts are illustrative simulations at 3% per year, not KBC rates or advice. Synthetic data.",
    "…": "…"
  }
}
```

## `POST /customers/lucas/events`

The server sets `id`, `timestamp` and `origin`. The body only carries `type`, `data` and, in demo mode, an optional `days_ago` (0 to 365). Unknown fields are rejected with 422.

Request: an unexpected €1,500 garage bill.

```json
{ "type": "TRANSACTION", "data": { "direction": "out", "amount": 1500, "category": "unexpected_expense", "merchant": "Garage Dupont" } }
```

Response (new `my-kbc` payload). Here Lucas had first explored investing (scenario `cashflow_shock`, step 0):

```json
{
  "moments": [
    { "type": "CASHFLOW_PRESSURE", "confidence": 1.0, "status": "ACTIVE", "…": "…" },
    { "type": "FIRST_SALARY", "confidence": 0.95, "status": "ACTIVE", "…": "…" },
    { "type": "INVESTMENT_INTEREST", "confidence": 0.9, "status": "ACTIVE", "…": "…" }
  ],
  "decision": {
    "decision_type": "SHOW_WARNING",
    "level": "PROACTIVE",
    "primary": { "journey": "CASHFLOW_SUPPORT", "score": 0.9635, "…": "…" },
    "secondary": [{ "journey": "FINANCIAL_FOUNDATION", "…": "…" }],
    "suppressed": [
      { "journey": "INVESTMENT_START", "rule": "CASHFLOW_RISK", "reason": "…", "score_before": "…" }
    ],
    "…": "…"
  },
  "experience": {
    "mode": "PROACTIVE",
    "hero": { "title": "Heads-up on your balance", "tone": "warning", "…": "…" },
    "primary_journey": {
      "type": "CASHFLOW_SUPPORT",
      "decision_type": "SHOW_WARNING",
      "actions": [
        { "id": "CASHFLOW_FORECAST", "kind": "INFO", "status": "AVAILABLE",
          "payload": { "current_balance": 1780.0, "projected_balance": 286.67, "days_until_next_income": 28, "next_income_date": "2026-10-29", "avg_monthly_spending": 1600.0 } },
        { "id": "UPCOMING_PAYMENTS", "…": "…" },
        { "id": "SPENDING_PAUSE_TIPS", "…": "…" },
        { "id": "TALK_TO_ADVISOR", "…": "…" }
      ],
      "…": "…"
    },
    "notices": [
      { "kind": "warning", "text": "Your balance may run low before your next income. New offers are paused until it recovers." }
    ],
    "…": "…"
  }
}
```

## `POST /customers/lucas/feedback`

Request:

```json
{ "journey": "FINANCIAL_FOUNDATION", "feedback": "NOT_RELEVANT" }
```

Response (new `my-kbc` payload). The journey is suppressed for 30 days, and nothing else is relevant enough, so the screen goes calm:

```json
{
  "decision": {
    "decision_type": "NO_ACTION",
    "level": "NONE",
    "primary": null,
    "suppressed": [
      { "journey": "FINANCIAL_FOUNDATION", "rule": "FEEDBACK_DISMISSED", "reason": "…", "score_before": "…" },
      { "journey": "INVESTMENT_START", "rule": "LOW_CONFIDENCE", "reason": "Intent confidence 0.14 is below 0.40.", "…": "…" }
    ],
    "…": "…"
  },
  "experience": {
    "mode": "CALM",
    "hero": { "title": "Everything looks on track.", "…": "…" },
    "primary_journey": null,
    "…": "…"
  }
}
```

`LATER` only lowers the journey's score by 0.25 for 7 days. `USEFUL` is recorded but changes nothing. `POST /customers/lucas/reset` restores the seed state.

## Errors

Every error has the same shape. There is no stack trace, and input values are never echoed.

```json
{ "error": { "code": "NOT_FOUND", "message": "Resource not found." } }
```
