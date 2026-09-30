# KBC Fit synthetic datasets

A generator for **100% synthetic** Belgian retail-banking data. It produces 10,000 customers over 24 months
(1 Oct 2024 to 30 Sep 2026), with:

- **Bank data:** every customer has accounts, insurance contracts and every transaction on them.
- **Website and app navigation:** sessions and clickstream on the KBC site and app.
- **Ground truth:** the real life events, kept in a separate database that a detector never reads.

Every transaction has a reason. A customer expecting a baby shops at baby stores in the third trimester,
visits a gynaecologist every month, receives the birth allowance, and then pays for childcare. A home buyer
pays a deposit to a notary, then deed costs; the rent stops, a mortgage starts, and the next weeks are full
of IKEA and DIY purchases. The same customer browsed the home-loan simulator for months before.

Built for the KBC challenge at Tectonic Hackathon. No real customer data is used anywhere.

## Run it

```bash
cd datasets
python3 -m kbcfit_data                                  # 10,000 customers -> output/ (about 6 minutes)
python3 -m kbcfit_data --customers 500 --out sample     # a small set
python3 -m kbcfit_data --csv                            # also write every table as CSV in output/csv/
```

It needs only `numpy` and `pandas` (see `requirements.txt`). The output is deterministic for a given
`--seed` (default 42), and customer `n` is the same whatever the total number of customers.
`--workers N` uses N processes; the default of 1 is a plain loop, because multiprocessing hangs in some sandboxes.

Each run writes `output/report.md`: volumes, balance checks, how visible each event is, and a check of the
demo personas. `output/` is ignored by Git, because the files are too large for the repository.

## Google Cloud

The datasets go to **BigQuery**, in three datasets located in the EU:

```bash
pip install google-cloud-bigquery
export GCP_PROJECT_ID=... GCP_CLIENT_EMAIL=... GCP_PRIVATE_KEY="..."   # the same variables as the app
python3 upload_bigquery.py --dry-run     # shows tables, row counts and schemas
python3 upload_bigquery.py               # loads kbcfit_bank, kbcfit_web, kbcfit_labels
```

The service account key is read from the environment and is never stored in Git. The labels are loaded into
their own dataset, so access to the ground truth can be restricted separately.

## The three databases

| File | Who may read it | Content |
|---|---|---|
| `bank.sqlite` | the detector, the app | What a bank observes: customers, accounts, transactions, contracts, declared situations |
| `web.sqlite` | the detector | What web analytics observe, only for customers who accepted analytics cookies |
| `labels.sqlite` | **evaluation only** | The truth: life events, which rows they caused, latent traits |

### `bank.sqlite`

| Table | One row per | Main columns |
|---|---|---|
| `customers` | customer | `customer_id`, name, `gender`, `birth_date`, `age`, `language` (nl/fr/en), `city`, `postcode`, `province`, `region` (FL/BR/WA), `customer_since`, `employment_status_kyc`, `marital_status_kyc`, `housing_status_kyc`, `children_known`, `risk_profile`, `consent_personalisation`, `consent_analytics`, `consent_marketing`, `has_mobile_app`, `demo_persona` |
| `accounts` | account | `account_id`, `customer_id`, `account_type`, `product_name`, `iban_masked` (only the last 4 digits), `opened_date`, `balance_start` (on 1 Oct 2024), `balance_end` (on 30 Sep 2026) |
| `transactions` | booked movement | `transaction_id`, `account_id`, `customer_id`, `account_type`, `booking_date`, `transaction_ts`, `amount` (signed: negative means money out), `direction`, `balance_after`, `category`, `mcc`, `channel`, `counterparty_name`, `counterparty_type`, `merchant_id`, `merchant_city`, `merchant_country`, `description` (bank-statement text), `is_recurring`, `original_currency`, `original_amount` |
| `insurance_contracts` | KBC Insurance policy | `product_type`, `start_date`, `end_date`, `yearly_premium`, `premium_frequency` |
| `declared_situations` | situation told by the customer in the app | `situation` (expecting_a_child, buying_a_home, moving, living_together, getting_married, lost_job, new_job, separating, retiring), `declared_date` |
| `monthly_balances` | account and month | `month`, `balance_end_of_month` |
| `merchants` | merchant | `name`, `category`, `mcc`, `is_online`, `city`, `country` |

The KYC columns hold what the bank recorded when the customer was onboarded. They are not updated by later
life events, the same as at a real bank. The true state on 30 Sep 2026 is in `labels.customer_truth`.

**Account types:** `current`, `savings`, `credit_card`, `pension_savings`, `long_term_savings`,
`investment_plan`, `home_loan`, `car_loan`, `child_savings`, `rental_guarantee`. Loans carry a negative balance
(the principal still owed). Insurance or loans held **outside KBC** appear only as payments to another
insurer or bank.

**Channels:** `card_pos`, `card_contactless`, `card_online`, `mobile_payment` (Payconiq), `credit_card`,
`atm`, `transfer_in`, `transfer_out`, `instant_transfer_in`, `instant_transfer_out`, `standing_order`,
`direct_debit`, `internal_transfer`, `loan_repayment`, `loan_disbursement`, `interest`, `fee`.

**Counterparty types:** `merchant`, `employer`, `client`, `government`, `social_security`, `person`,
`own_account`, `bank`, `insurer`, `utility`, `telecom`, `landlord`, `notary`, `healthcare`, `school`,
`childcare`, `subscription`, `charity`, `atm`.

**Categories** include everyday spending (groceries, bakery, restaurant, fuel...), life-moment spending (`baby`
MCC 5641, `car_dealer` MCC 5511, `furniture`, `legal_notary`, `wedding_services`, `childcare`, `education`...),
income (`salary`, `pension`, `child_benefit`, `unemployment_benefit`, `business_income`), housing (`rent`,
`mortgage`, `energy`, `water`, `telecom`) and transfers (`own_transfer`, `p2p`, `card_settlement`).
**Health categories** (`pharmacy`, `medical`, `dentist`, `hospital`, `health_refund`, `health_insurance`,
`maternity_benefit`) and `charity` are special-category data under GDPR article 9. They are generated so that
the balances add up, but a detector must not read them.

### `web.sqlite`

| Table | Content |
|---|---|
| `pages` | The site and app catalogue: `page_id`, `path`, `section` (app / website), `topic`, `page_type`. The structure is illustrative, not the real kbc.be sitemap |
| `sessions` | `session_id`, `customer_id`, `start_ts`, `end_ts`, `platform` (ios_app, android_app, web_desktop, web_mobile), `is_authenticated`, `traffic_source`, `campaign_id`, `entry_page`, `exit_page`, `n_events`, `language` |
| `web_events` | `event_id`, `session_id`, `customer_id`, `event_type`, `event_ts`, `page_id`, `page_path`, `section`, `topic`, `step` (landing, article, help, app_screen, product, life_moment, tool, simulator, form, search, kate), `element`, `search_query`, `kate_intent`, `params` (JSON, for example the amount entered in a simulator), `transaction_id` (on transfer confirmations), `dwell_seconds` |
| `campaigns` | The email campaigns sent to customers who accepted marketing |

**Event types:** `page_view`, `click`, `search`, `simulator_start`, `simulator_submit`, `kate_message`,
`form_start`, `form_submit`, `appointment_booked`, `application_submitted`, `transfer_confirmed`,
`offer_impression`, `offer_click`, `offer_dismiss`.

`offer_impression` rows are the generic banners that today's app shows to everyone (loan, insurance, savings...).
They are the "BEFORE" screen of KBC Fit, measured: the click-through rate is under 1%.

### `labels.sqlite` (never read by a detector)

| Table | Content |
|---|---|
| `life_events` | `event_id`, `customer_id`, `event_type`, `event_class` (life_event or distractor), `event_date`, `status` (past, or upcoming on 30 Sep 2026), `trace_level`, `declared_by_customer`, `declared_date`, `details` |
| `transaction_signals` | `event_id`, `transaction_id`, `signal`: the transactions an event caused |
| `web_signals` | `event_id`, `web_event_id`, `signal`: the web events an event caused |
| `customer_truth` | The true state on 30 Sep 2026 (employment, housing, partner, children, car) and the hidden traits the generator used |
| `external_products` | Insurance and loans held outside KBC |

## How the data is generated

1. **Profile.** An archetype (student, starter, couple, young family, family, single, empty nester, retiree)
   sets the age, household, job, income, housing and car. The customer lives in one of 53 Belgian cities (70%
   Flanders, 15% Brussels, 15% Wallonia) and has hidden traits: eats out, shops online, uses cash, travels,
   saves, digital affinity.
2. **Life events** are sampled from the profile (see the table below). Their dates can fall before 30 Sep 2026
   or after it: a pregnancy can still be in progress, or a home purchase still at the simulator stage. That
   gives forecasting cases.
3. **Streams.** Salary on the last business day, with holiday pay in May and an end-of-year bonus in December.
   Also pension, child benefit, rent, mortgage, energy advances with a yearly settlement, water, telecom,
   insurance premiums, subscriptions, taxes and savings orders. The streams start and stop with the events.
4. **Day-to-day spending**: about 30 categories drawn day by day. It follows the weekday, the hour, each
   customer's favourite shops and trips abroad (foreign merchants, other currencies). It is calibrated so that
   spending fits what is left after fixed costs.
5. **Balances.** Savings absorb big payments (house deposit, car). Money sweeps to savings at the end of the
   month for customers who do that, and the current account is topped up when it runs low. Idle-cash customers
   keep everything on the current account.
6. **Web.** App sessions for checking the balance, more often after payday. Sessions for transfers the customer
   really made. Research sessions driven by the events (simulator inputs match the real price). Application
   sessions on the day a product was opened in the bank data. Declarations in "my situation". Campaign clicks.

### Events

| Event | Main traces in the data |
|---|---|
| `birth` | Baby stores (big purchases in the third trimester), monthly prenatal visits and health refunds, birth allowance (in Flanders 2 months before the due date), hospital bill, birth cards, sugared almonds at a chocolatier, maternity benefit replacing the salary, child benefit, childcare, more drugstore and fewer restaurant visits. Web: "having a baby", child savings, hospitalisation insurance |
| `home_purchase` | 10% deposit to a notary, deed costs and registration duties, rent stops, mortgage starts (KBC or another bank), rental guarantee released, movers, IKEA, DIY. Web: home-loan simulator for months, with the real amount |
| `first_job` | Student jobs and pocket money stop, salary starts, savings order starts |
| `moving_out` | Rental guarantee, first rent, utilities, furniture, groceries up |
| `cohabitation` | Contribution from the partner, new rent, furniture |
| `wedding` | Venue deposit, rings, photographer, caterer, gifts received, honeymoon abroad |
| `car_purchase` | Payment to a car dealer or a car loan, new car insurance, fuel starts |
| `job_loss` | Salary stops, severance pay, unemployment benefit, spending down |
| `new_job` | Employer changes, salary changes |
| `retirement` | Salary stops, pension starts, often a group-insurance lump sum that then sits idle |
| `inheritance` | A large transfer from a notary, sometimes funeral costs before |
| `separation` | Partner contribution stops, lawyer, new rent, furniture |
| `child_to_higher_education` | Tuition fee, student room rent, pocket money to the child |

### Noise, on purpose

A detector that scores 100% proves nothing. So the data contains:

- **Distractors**, events that look like a target but are not one:
  - grandparents buying baby gifts (`grandchild_born`), and a gift for a friend's baby;
  - business trips, refunded by the employer;
  - renovations, which look like a home purchase in DIY spending;
  - a big one-off purchase;
  - browsing the home-loan or car-loan simulator without buying.
- **Trace levels.** Each life event is `strong`, `medium`, `weak` or `none`. A `weak` birth may be only a few
  second-hand purchases and a child benefit paid to the partner's account elsewhere. A `none` event leaves
  nothing: the partner paid for everything from another bank. Score a detector by trace level.
- **Partial observation.** Insurance and loans held elsewhere show only as payments. Half the child benefit goes
  to the partner's account. KYC data is out of date. 22% of customers refused analytics cookies, so they have
  no web data.

Rates are higher than Belgian statistics (for example about 6% of customers have a birth in the window), so
every event has enough positive cases for machine learning.

## The four demo personas

Customers `C0000001` to `C0000004` are the personas of the KBC Fit site. On 30 Sep 2026 their balances and
account digits match `src/lib/data/personas.ts`:

| Persona | Story in the data |
|---|---|
| Lucas (C0000001) | Student room in Ghent, first job on 1 Mar 2026 (€2,450 net), moves into a flat in April. Current account €2,340, savings €1,800, no pension savings |
| Thomas (C0000002) | Homeowner in Leuven, saves €150 every month, his first child was born on 24 Aug 2026 and he told the bank in the app on 2 Sep 2026. Savings €2,400, no long-term savings |
| Monique (C0000003) | Retired widow in Hasselt, pension every month, about 21 movements and €2,500 spent a month. €54,400 on the current account |
| Claire (C0000004) | Self-employed architect in Mechelen, two children, mortgage, invested savings, pension savings, all insurance at KBC. Nothing to suggest |

### How the app reads them

```bash
python3 -m kbcfit_data --customers 4 --out output_personas   # the four personas only, in seconds
python3 export_personas.py                                    # -> src/lib/data/personas.generated.json
GCP_PROJECT_ID=... GCP_CLIENT_EMAIL=... GCP_PRIVATE_KEY="..." node ../scripts/seed-firestore.mjs   # -> Firestore
```

The app (`src/lib/data/store.ts`) reads the personas from Firestore on the server and falls back to the
bundled `personas.generated.json` when Firestore is not configured or unreachable. The accounts, balances and
signal details on screen come from the database. The narrative and the scenario parameters stay in
`src/lib/data/personas.ts`.

## Using it for machine learning

- **Point in time.** To predict at date D, read only rows dated before D. Life events have dates, so a model can
  be trained on snapshots (for example quarterly) without looking into the future.
- **No leakage.** Do not read `labels.sqlite` in features. `declared_situations` is legitimate: the customer
  told the bank.
- **Suggested tasks:** detect a life event (per event type, scored by trace level), predict the next product
  opened (accounts and contracts opened in the window carry the date), idle-cash detection, banner relevance.
- **The ML model** in `../ml/` maps these tables onto its data contract with its own adapter.

## Limits

- Synthetic. It shows that a pipeline can recover what the generator planted, through the noise it adds. It
  says nothing about the scores on real KBC data.
- Real Belgian chains and public bodies appear as merchant or payer names so that statements look real.
  Employers, landlords, local shops, doctors and every person are fictional.
- The amounts are plausible orders of magnitude (2025 levels), not official rates or tariffs.
- Each customer is simulated alone: partners and family members are not customers themselves.
