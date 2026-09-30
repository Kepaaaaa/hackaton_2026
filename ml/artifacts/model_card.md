# KBC Fit signal model: model card

- Version: `20260930-193354-synthetic-3k`
- Trained on: **synthetic-3k**, 3,000 customers, snapshots 2026-09-30, 2026-07-01, 2026-04-01, 2025-12-31
- A card is shown when confidence >= 0.6 (confidence = sum of the active signal weights)
- Scores below are measured on customers held out of training (20%)

| Event | Labelled cases | AUC expert priors | AUC learned | AUC black box | Precision @0.6 | Recall @0.6 |
|---|---:|---:|---:|---:|---:|---:|
| A baby on the way or just born (sensitive) | 237 | 0.87 | **0.86** | 0.86 | 0.96 | 0.45 |
| Buying a home | 80 | 0.79 | **0.78** | 0.77 | 0.83 | 0.24 |
| Buying a car | 144 | 0.76 | **0.80** | 0.83 | 0.83 | 0.34 |
| First job | 45 | 0.82 | **0.82** | 0.18 | 0.70 | 0.64 |
| Moving out | 28 | - | not trained | - | - | - |
| Moving in together | 35 | 0.64 | **0.64** | - | 0.00 | 0.00 |
| Getting married | 37 | 0.83 | **0.83** | 0.50 | 0.00 | 0.00 |
| Job loss (sensitive) | 45 | 0.85 | **0.85** | 0.75 | 0.75 | 0.60 |
| New job | 102 | 0.91 | **0.91** | 0.91 | 0.68 | 0.81 |
| Retirement | 63 | 0.86 | **0.86** | 0.86 | 1.00 | 0.75 |
| Inheritance received (sensitive) | 20 | - | not trained | - | - | - |
| Separation (sensitive) | 22 | - | not trained | - | - | - |
| A child starting higher education | 25 | - | not trained | - | - | - |
| Travel coming up | 0 | - | not trained | - | - | - |

## Weights (expert prior -> learned)

**A baby on the way or just born**

- Situation you told us about: 0.50 -> **0.64** (seen 68 times)
- Several purchases in baby stores: 0.30 -> **0.16** (seen 293 times)
- Child benefit payments started: 0.40 -> **0.32** (seen 34 times)
- Childcare payments started: 0.30 -> **0.30** (seen 18 times, too rare to learn: prior kept)
- Photo print order: 0.05 -> **0.05** (seen 16 times, too rare to learn: prior kept)
- Read the 'Having a baby' pages: 0.20 -> **0.04** (seen 1,062 times)
- Looked at saving for a child: 0.10 -> **0.12** (seen 422 times)

**Buying a home**

- Situation you told us about: 0.50 -> **0.15** (seen 20 times)
- Large payment to a notary: 0.45 -> **0.59** (seen 65 times)
- Rent payments stopped: 0.20 -> **0.00** (seen 30 times)
- Payment to a moving company: 0.15 -> **0.00** (seen 21 times)
- Unusually high furniture and DIY spending: 0.15 -> **0.00** (seen 135 times)
- Looked at home loans: 0.15 -> **0.00** (seen 872 times)
- Used the home-loan simulator: 0.25 -> **0.06** (seen 316 times)

**Buying a car**

- Large payment to a car dealer: 0.55 -> **0.58** (seen 93 times)
- Fuel spending started: 0.20 -> **0.00** (seen 20 times)
- Looked at car loans or car insurance: 0.15 -> **0.00** (seen 2,841 times)
- Used the car-loan simulator: 0.20 -> **0.11** (seen 460 times)

**First job**

- A salary started to arrive: 0.55 -> **0.55** (seen 1 times, too rare to learn: prior kept)
- Salary from a new employer: 0.20 -> **0.09** (seen 106 times)
- Read the 'Your first job' pages: 0.15 -> **0.63** (seen 42 times)

**Moving out** (not trained: fewer than 30 labelled cases: expert priors kept)

- Situation you told us about: 0.50 -> **0.50** (seen 5 times)
- Rent payments started: 0.40 -> **0.40** (seen 19 times)
- Rental deposit paid: 0.30 -> **0.30** (seen 17 times)
- Payment to a moving company: 0.10 -> **0.10** (seen 21 times)
- Unusually high furniture and DIY spending: 0.10 -> **0.10** (seen 135 times)
- Read the 'Moving out' pages: 0.15 -> **0.15** (seen 18 times)

**Moving in together**

- Situation you told us about: 0.50 -> **0.50** (seen 5 times, too rare to learn: prior kept)
- Rent payments started: 0.20 -> **0.20** (seen 19 times, too rare to learn: prior kept)
- Payment to a moving company: 0.10 -> **0.00** (seen 21 times)
- Read the 'Living together' pages: 0.25 -> **0.25** (seen 19 times, too rare to learn: prior kept)

**Getting married**

- Situation you told us about: 0.50 -> **0.50** (seen 5 times, too rare to learn: prior kept)
- Payments to wedding services: 0.45 -> **0.24** (seen 42 times)
- Jewellery purchase: 0.20 -> **0.19** (seen 31 times)
- Read the 'Getting married' pages: 0.20 -> **0.09** (seen 30 times)

**Job loss**

- Situation you told us about: 0.50 -> **0.50** (seen 6 times, too rare to learn: prior kept)
- Unemployment benefit started: 0.60 -> **0.23** (seen 39 times)
- Salary payments stopped: 0.30 -> **0.00** (seen 68 times)
- Read the 'Losing your job' pages: 0.20 -> **0.42** (seen 46 times)

**New job**

- Situation you told us about: 0.50 -> **0.50** (seen 10 times, too rare to learn: prior kept)
- Salary from a new employer: 0.60 -> **0.73** (seen 106 times)

**Retirement**

- Situation you told us about: 0.50 -> **0.50** (seen 0 times, too rare to learn: prior kept)
- Pension payments started: 0.60 -> **0.94** (seen 38 times)
- Salary payments stopped: 0.25 -> **0.01** (seen 68 times)
- Large insurance payout received: 0.20 -> **0.20** (seen 7 times, too rare to learn: prior kept)
- Read the 'Preparing your retirement' pages: 0.15 -> **0.01** (seen 1,041 times)

**Inheritance received** (not trained: fewer than 30 labelled cases: expert priors kept)

- Large transfer received from a notary: 0.60 -> **0.60** (seen 24 times)
- Read the 'Receiving an inheritance' pages: 0.20 -> **0.20** (seen 31 times)

**Separation** (not trained: fewer than 30 labelled cases: expert priors kept)

- Situation you told us about: 0.50 -> **0.50** (seen 5 times)
- Rent payments started: 0.20 -> **0.20** (seen 19 times)
- Read the 'Separating' pages: 0.35 -> **0.35** (seen 17 times)

**A child starting higher education** (not trained: fewer than 30 labelled cases: expert priors kept)

- University fees paid: 0.50 -> **0.50** (seen 38 times)
- Rent payments started: 0.15 -> **0.15** (seen 19 times)
- Read the 'Children going to university' pages: 0.20 -> **0.20** (seen 43 times)

**Travel coming up** (not trained: fewer than 30 labelled cases: expert priors kept)

- Flight booked: 0.40 -> **0.40** (seen 1,151 times)
- Accommodation or package holiday booked: 0.30 -> **0.30** (seen 1,467 times)
- Card payments abroad: 0.20 -> **0.20** (seen 320 times)
- Read about paying abroad or travel insurance: 0.20 -> **0.20** (seen 1,472 times)

