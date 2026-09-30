# KBC Context moments: hand-set vs learned weights

Backend pipeline run on 2,462 synthetic customers at 2026-09-30, 2026-06-30, 2026-03-31, 2025-12-31. Scores on held-out customers (20%), a moment counts when ACTIVE (>= 0.40).

| Moment | Cases | AUC hand-set | AUC learned | Precision hand-set -> learned | Recall hand-set -> learned |
|---|---:|---:|---:|---:|---:|
| FIRST_SALARY | 39 | 0.84 | **0.50** | 0.00 -> 0.00 | 0.00 -> 0.00 |
| NEW_PARENT | 192 | 0.88 | **0.88** | 1.00 -> 1.00 | 0.21 -> 0.26 |
| RETIREMENT_TRANSITION | 51 | 0.93 | **0.87** | 1.00 -> 1.00 | 0.25 -> 0.12 |
| TRAVEL | 0 | - | fewer than 30 cases | - | - |
| CAR_PROJECT | 125 | 0.78 | **0.78** | - -> 1.00 | 0.00 -> 0.44 |
| HOME_BUYING | 65 | 0.85 | **0.82** | 0.30 -> - | 0.64 -> 0.00 |
| CASHFLOW_PRESSURE | 0 | - | no ground truth for this moment | - | - |
| LARGE_CASH_INFLOW | 16 | - | fewer than 30 cases | - | - |
| INVESTMENT_INTEREST | 0 | - | no ground truth for this moment | - | - |

## Weights

**FIRST_SALARY**
- FIRST_RECURRING_SALARY: 0.70 -> **0.70** (seen 3 times)
- SALARY_RECEIVED: 0.15 -> **0.00** (seen 6,606 times)
- LOW_EMERGENCY_BUFFER: 0.10 -> **0.01** (seen 1,715 times)

**NEW_PARENT**
- PARENTHOOD_DECLARED: 0.55 -> **0.66** (seen 40 times)
- CHILD_ACCOUNT_OPENED: 0.25 -> **0.25** (seen 0 times)
- CHILD_RELATED_EXPENSE: 0.20 -> **0.19** (seen 554 times)
- NEW_RECURRING_CHILD_EXPENSES: 0.15 -> **0.15** (seen 9 times)
- CHILD_SAVINGS_PAGE_VIEW: 0.10 -> **0.29** (seen 305 times)

**RETIREMENT_TRANSITION**
- RECURRING_PENSION_STARTED: 0.45 -> **0.45** (seen 14 times)
- SALARY_STOPPED: 0.35 -> **0.28** (seen 81 times)
- RETIREMENT_DECLARED: 0.30 -> **0.30** (seen 0 times)
- RETIREMENT_PAGE_VIEW: 0.10 -> **0.04** (seen 562 times)
- HIGH_IDLE_CASH: 0.10 -> **0.00** (seen 5,182 times)

**TRAVEL** (fewer than 30 cases)
- AIR_TRAVEL_ACTIVITY: 0.35 -> **0.35** (seen 423 times)
- HOTEL_BOOKING: 0.25 -> **0.25** (seen 580 times)
- TRAVEL_PAGE_VIEW: 0.20 -> **0.20** (seen 946 times)
- FOREIGN_PAYMENT_SETTINGS_VIEWED: 0.20 -> **0.20** (seen 4,174 times)

**CAR_PROJECT**
- AUTOMOTIVE_TRANSACTION: 0.25 -> **0.94** (seen 59 times)
- ELECTRIC_CAR_LOAN_PAGE_VIEW: 0.30 -> **0.30** (seen 0 times)
- ELECTRIC_CAR_LOAN_SIMULATION: 0.30 -> **0.30** (seen 0 times)
- CAR_FINANCING_KBC_SEARCH: 0.15 -> **0.12** (seen 244 times)

**HOME_BUYING**
- MORTGAGE_SIMULATION: 0.35 -> **0.12** (seen 152 times)
- REPEATED_MORTGAGE_SIMULATION: 0.25 -> **0.44** (seen 27 times)
- MORTGAGE_PAGE_VIEW: 0.25 -> **0.00** (seen 518 times)
- HOME_KBC_SEARCH: 0.15 -> **0.07** (seen 169 times)

**CASHFLOW_PRESSURE** (no ground truth for this moment)
- LOW_PROJECTED_BALANCE: 0.55 -> **0.55** (seen 875 times)
- LARGE_UNEXPECTED_EXPENSE: 0.35 -> **0.35** (seen 0 times)
- LOW_EMERGENCY_BUFFER: 0.10 -> **0.10** (seen 1,715 times)

**LARGE_CASH_INFLOW** (fewer than 30 cases)
- LARGE_CASH_INFLOW: 0.80 -> **0.80** (seen 129 times)
- HIGH_IDLE_CASH: 0.20 -> **0.20** (seen 5,182 times)

**INVESTMENT_INTEREST** (no ground truth for this moment)
- INVESTMENT_SIMULATION: 0.40 -> **0.40** (seen 0 times)
- INVESTMENT_PAGE_VIEW: 0.30 -> **0.30** (seen 2,388 times)
- INVESTMENT_KBC_SEARCH: 0.20 -> **0.20** (seen 475 times)

