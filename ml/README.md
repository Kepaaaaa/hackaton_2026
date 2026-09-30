# KBC Fit signal model

Reads a customer's transactions and website visits, detects the life moments that open a
real need (a baby on the way, a car purchase, a home purchase…), and writes one JSON per
customer for the KBC Fit engine: **what we detected, how sure we are, and why**.

It is trained here on 100% synthetic data. **Nothing in it is tied to that data**: the model
reads four plain tables (the *data contract*), and learns its weights from the outcomes it is
given. Point it at KBC's own tables and outcomes, and it retrains on them with the same command.

```
 synthetic generator ─┐                                   ┌─> model.json + model_card.md
 (datasets/)          ├─> adapter ─> data contract ─> train
 KBC data warehouse ──┘              (4 CSV tables)       └─> predict ─> one JSON per customer ─> engine
```

## Run it

```bash
cd ml
pip install -r requirements.txt
python -m kbcfit_ml.adapters.synthetic --src ../datasets/output --out data/synthetic   # generator -> contract
python -m kbcfit_ml train   --data data/synthetic          # learns weights, writes artifacts/model_card.md
python -m kbcfit_ml predict --data data/synthetic --customer C0000001
python -m kbcfit_ml predict --data data/synthetic --out predictions.jsonl
python -m pytest                                            # 10 tests, a few seconds (11 with the backend)
```

## Training it on your own data

1. **Map your tables to the contract.** This is the only code to write: one adapter that
   produces these files. [`adapters/synthetic.py`](kbcfit_ml/adapters/synthetic.py) is the
   one for our generator (about 150 lines). It also shows the two rules an adapter must
   follow:
   - **Keep only what the bank observes.** A transfer the generator labels `inheritance`
     becomes "money received from a notary", and the answer-key columns are dropped.
   - **Remove outcomes.** A loan the bank granted or an online application is a result to
     predict, not a signal to use.

   | File | Columns | Where it comes from at a bank |
   |---|---|---|
   | `customers.csv` | `customer_id`, `consent_transactions`, `consent_search` | Customer master, consent registry |
   | `transactions.csv` | `customer_id`, `transaction_id`, `booking_date`, `amount` (negative = out), `category`, `counterparty`, `country` | Booked transactions. `category` comes from the existing categorisation (MCC codes for cards, counterparty type for transfers) |
   | `web_events.csv` | `customer_id`, `timestamp`, `topic`, `step`, `page`, `session_id` | Web and app analytics, for customers who consented |
   | `declarations.csv` *(optional)* | `customer_id`, `event`, `declared_date` | What the customer told the bank ("my situation" in the app) |
   | `labels.csv` *(training only)* | `customer_id`, `event`, `event_date` | See step 2 |

   The allowed `category` and `step` values are listed in
   [`kbcfit_ml/contract.py`](kbcfit_ml/contract.py). Loading fails loudly on anything unknown.

2. **Build labels from outcomes you already record.** No manual labelling is needed:

   | Event | A real outcome that can serve as its label |
   |---|---|
   | `birth` | Child added to a hospitalisation policy, child savings account opened, situation declared |
   | `home_purchase` | Mortgage application or deed signed |
   | `car_purchase` | Car loan or car insurance taken out |
   | `retirement` | First pension payment booked |
   | `job_loss` | Unemployment benefit booked, payment holiday requested |
   | `travel` | Travel insurance bought, card limit raised for abroad |

   Here the labels are the generator's ground truth. At a bank they are the outcomes above.

3. **Train.** `python -m kbcfit_ml train --data <folder> --source kbc-2026Q3`.
   - **Point in time.** The model rebuilds the customer's situation at several past dates
     (every quarter by default). Each snapshot only reads data dated before it, so the model
     never learns from the future.
   - **Held-out test.** 20% of customers are kept out of training. All scores in the model
     card are measured on them.

4. **Read the model card** (`artifacts/model_card.md`). For every event it compares:
   - **expert priors**: the hand-set weights;
   - **learned** weights;
   - **a black-box gradient-boosting model** trained on the same signals.

   It also gives precision and recall at the engine's 0.6 threshold.

5. **Predict.** `python -m kbcfit_ml predict --data <folder> --out predictions.jsonl`.

**Day one, before any outcome is known:** `predict --expert-priors` runs with the hand-set
weights. The `travel` event works this way even here, because the synthetic data has no
travel labels. As outcomes accumulate, `train` replaces the priors event by event. An event
keeps its priors until it has at least 30 labelled cases.

## How it decides

- **Signals are rules that encode banking knowledge.** A rule says *where* to look, for
  example "a large payment to a notary" or "child benefit started this quarter, never
  before". The rules are data in [`kbcfit_ml/catalog.py`](kbcfit_ml/catalog.py). Adding a case
  means adding a rule, with no model code to change.
- **Weights are learned.** A rule never says how much it counts: training measures that on
  the outcomes. A signal that fires for grandparents buying baby gifts as often as for
  parents ends up with a weight close to zero.
- **The model is additive on purpose.** Confidence = the sum of the weights of the active
  signals, capped at 1. That is exactly the engine's rule (`src/lib/engine/types.ts`), so the
  app can switch one signal off and recompute the confidence on the spot. The model card
  shows what this explainability costs compared with the black box.

## Privacy by design

- **No consent, no reading.** A customer's transactions or visits are dropped at load time,
  before any rule runs.
- **Health and belief data are never read.** Pharmacy, doctors, hospitals, health
  reimbursements and donations are special-category data under GDPR art. 9. They are dropped
  on load, and a test fails if a rule ever asks for them.
- **Sensitive events are never proposed on inference alone.** A birth, a job loss, a
  separation or an inheritance gets `"status": "ask_customer"` unless the customer declared
  it. The app then asks; it does not sell.
- **No free text leaves the model.** Site search queries count towards a topic, but their
  text is not copied into the JSON.
- **Runs inside the bank.** It uses plain numpy, pandas and scikit-learn. There is no
  external API and no language model.

## Output

One JSON per customer. The `signals` objects follow the engine's frozen `Signal` type (`id`,
`label`, `detail`, `source`, `weight`), with `evidence` added: the ids of the transactions or
pages behind the signal, for "See what we checked".

```json
{
  "customer_id": "C0000001",
  "as_of": "2026-09-30",
  "model": { "version": "…-synthetic", "source": "synthetic", "threshold": 0.6 },
  "consent": { "transactions": true, "search": true },
  "transactions": [
    {
      "event": "car_purchase", "label": "Buying a car", "confidence": 0.9, "status": "ready",
      "sensitive": false, "products": ["car_loan", "car_insurance"],
      "signals": [
        { "id": "car_dealer_payment", "label": "Large payment to a car dealer",
          "detail": "€18,500 on 10 Sep 2026 (Garage Maes)", "source": "transactions",
          "weight": 0.55, "evidence": ["T59"] },
        { "id": "car_loan_simulator", "label": "Used the car-loan simulator",
          "detail": "1 visit, last on 25 Sep 2026", "source": "search",
          "weight": 0.2, "evidence": ["web_car_loan_sim"] }
      ]
    }
  ],
  "searches": [
    { "topic": "car_loan", "label": "Car loans", "score": 0.37, "events": 1, "sessions": 1,
      "last_visit": "2026-09-25", "deepest_step": "simulator", "top_pages": ["web_car_loan_sim"],
      "products": ["car_loan", "car_insurance"], "sensitive": false }
  ]
}
```

| Field | Meaning |
|---|---|
| `transactions[].event` | Life event detected, from transactions (plus a supporting visit or a declaration when there is one) |
| `transactions[].status` | One of three values, see below |
| `searches[].score` | Interest in a topic, from 0 to 1. Deeper steps count more (a simulator counts 6× an article), and a visit counts half as much every 14 days |

The three values of `status`:

- `ready`: confidence ≥ 0.6, can be proposed.
- `ask_customer`: sensitive event, the customer must confirm first.
- `below_threshold`: shown to nobody.

## Link with the KBC Context backend (branch `Mathias`)

The backend on branch `Mathias` (`backend/`) is the decision pipeline: signals → moments →
intents → journeys → experience. Its moments use the same additive formula as this model:
confidence = min(1, Σ weight × strength). That makes the two pieces complementary:
- **the dataset** gives the backend 3,000–10,000 realistic customers instead of 4 seed personas;
- **this training code** learns the backend's moment weights from outcomes, instead of setting
  them by hand.

The link lives in [`kbcfit_ml/bridges/kbc_context.py`](kbcfit_ml/bridges/kbc_context.py). It
converts contract data into the backend's own `Customer` and `CustomerEvent` models, runs the
backend's own engines, and injects learned weights through
`ContextEngine(rules=learned_rules(...))`. **The backend code is not changed.**

```bash
git worktree add ../mathias origin/Mathias          # or any checkout of the branch
python -m kbcfit_ml.bridges.kbc_context run   --backend ../mathias/backend --data data/synthetic --customer C0000002
python -m kbcfit_ml.bridges.kbc_context learn --backend ../mathias/backend --data data/synthetic --sample 3000
KBC_CONTEXT_BACKEND=../mathias/backend python -m pytest    # 11 tests, including the bridge
```

`learn` writes `artifacts/kbc_context_moment_weights.json` and a report
([`artifacts/kbc_context_moment_weights.md`](artifacts/kbc_context_moment_weights.md)) that
compares the hand-set and learned weights on held-out customers.

**What is never learned:** the TTLs, and the `requires_any` cap. That cap keeps `NEW_PARENT`
at or below 0.35 until the customer declares it, whatever the weights; a test checks this.

**What the first run shows (3,000 synthetic customers):**
- **`CAR_PROJECT` never fired with the hand-set rules.** Only the *electric* car-loan page and
  simulator have a rule. Learning raises the weight of the car-dealer payment from 0.25 to
  about 0.9, and recall at the 0.40 threshold goes from 0 to 0.44 at precision 1.00. Adding a
  rule for the `car_loan` page is a one-line change in `rules/signals.py`.
- **`HOME_BUYING` with hand-set weights fires on people who only browse the simulator.**
  Precision is 0.30, so 70% of the cards shown are wrong. Learned weights show none; the
  model prefers proposing nothing.
- **`FIRST_RECURRING_SALARY` and `RECURRING_PENSION_STARTED` fire rarely on this data.**
  Their weights are kept as priors until there are enough cases.
- The mappings are approximate, for three reasons:
  - the backend has 22 transaction categories, against 60 in the contract;
  - its customer profile is filled with neutral defaults;
  - its `KBC_SEARCH` receives a text built from the topic, because the contract never carries
    the customer's own words.

## Limits

- The data is synthetic. The scores show that the pipeline recovers what the generator
  planted, through the noise and decoys it adds on purpose. They are not a forecast of the
  scores on real data. Retraining on KBC data gives the real numbers.
- The engine's frozen `SignalSource` type does not include `"search"` yet. It needs a team
  sync before the app can show website signals.
