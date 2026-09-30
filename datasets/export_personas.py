"""Export the four demo personas from the generated bank database to the app.

    python3 -m kbcfit_data --customers 4 --out output_personas     # the personas only (seconds)
    python3 export_personas.py --db output_personas/bank.sqlite

Writes ../src/lib/data/personas.generated.json: real accounts, balances and signal facts computed from
each persona's transactions. The app bundles it as its fallback and seeds Firestore with it
(scripts/seed-firestore.mjs). Customer n is identical in a 4-customer run and in the 10,000-customer run.
"""
import argparse
import json
import sqlite3
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "src" / "lib" / "data" / "personas.generated.json"
KINDS = {"current": ("current", "KBC Current Account"), "savings": ("savings", "Savings Account"),
         "investment_plan": ("investment", "Investment Portfolio"), "pension_savings": ("pension", "Pension Savings")}
AS_OF = "2026-09-30"


def monthly_flows(tx):
    cur = tx[(tx.account_type == "current") & (tx.category != "own_transfer") & (tx.category != "card_settlement")]
    card = tx[tx.account_type == "credit_card"]
    spend = pd.concat([cur[cur.amount < 0], card[card.amount < 0]])
    m_out = (-spend.groupby(spend.booking_date.str[:7]).amount.sum())
    m_in = cur[cur.amount > 0].groupby(cur[cur.amount > 0].booking_date.str[:7]).amount.sum()
    n = cur.groupby(cur.booking_date.str[:7]).size()
    return m_in, m_out, n


def eur(x):
    return f"€{x:,.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(HERE / "output_personas" / "bank.sqlite"))
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    customers = pd.read_sql_query("SELECT * FROM customers WHERE demo_persona IS NOT NULL", con)
    result = {"asOf": AS_OF, "source": "datasets/kbcfit_data (synthetic)", "personas": {}}
    for c in customers.itertuples():
        pid = c.demo_persona
        acc = pd.read_sql_query("SELECT * FROM accounts WHERE customer_id = ?", con, params=[c.customer_id])
        tx = pd.read_sql_query("SELECT * FROM transactions WHERE customer_id = ? ORDER BY transaction_ts", con,
                               params=[c.customer_id])
        contracts = pd.read_sql_query("SELECT * FROM insurance_contracts WHERE customer_id = ?", con, params=[c.customer_id])
        declared = pd.read_sql_query("SELECT * FROM declared_situations WHERE customer_id = ?", con, params=[c.customer_id])
        accounts = [{"id": f"{pid}-{KINDS[a.account_type][0]}", "label": KINDS[a.account_type][1], "last4": a.last4,
                     "balance": round(a.balance_end, 2), "kind": KINDS[a.account_type][0]}
                    for a in acc.itertuples() if a.account_type in KINDS]
        order = ["current", "savings", "investment", "pension"]
        accounts.sort(key=lambda a: order.index(a["kind"]))
        m_in, m_out, n_moves = monthly_flows(tx)
        facts = {}
        cur = tx[tx.account_type == "current"]
        salary = cur[(cur.category == "salary") & (cur.amount > 1000)]
        if len(salary):
            employer = salary.counterparty_name.iloc[-1]
            same = salary[salary.counterparty_name == employer]
            first_month = same.description.str.extract(r"SALARY (\d\d)/(\d{4})").dropna().iloc[0]
            months = (2026 - int(first_month[1])) * 12 + 9 - int(first_month[0]) + 1
            facts["salary"] = {"employer": employer, "monthsWithEmployer": int(months),
                               "netMonthly": round(float(same.amount.iloc[-3:].mean()), 0)}
            since = same.booking_date.iloc[0][:7]
            margin = (m_in[m_in.index >= since] - m_out[m_out.index >= since]).dropna()
            facts["avgMonthlyLeft"] = round(float(margin.mean()), 0)
        pension = cur[cur.category == "pension"]
        if len(pension):
            facts["pension"] = {"payer": pension.counterparty_name.iloc[-1], "netMonthly": round(float(pension.amount.iloc[-1]), 0)}
        orders = tx[(tx.account_type == "savings") & (tx.description.str.contains("MONTHLY SAVINGS"))]
        if len(orders):
            facts["savingsOrder"] = {"since": orders.booking_date.iloc[0][:7], "monthly": round(float(orders.amount.iloc[-1]), 0)}
        facts["avgMonthlySpent"] = round(float(m_out.mean()), 0)
        facts["avgMovementsPerMonth"] = round(float(n_moves.mean()), 0)
        sav = next((a["balance"] for a in accounts if a["kind"] == "savings"), 0)
        facts["cushionMonths"] = round(sav / max(1, facts["avgMonthlySpent"]), 1)
        invest = tx[(tx.account_type == "current") & tx.description.str.contains("INVESTMENT PLAN")]
        if len(invest):
            facts["investmentPlanMonthly"] = round(float(-invest.amount.iloc[-1]), 0)
        facts["kbcInsurance"] = sorted(contracts[contracts.end_date.isna()].product_type.unique().tolist())
        facts["heldProducts"] = sorted(acc.account_type.unique().tolist())
        if len(declared):
            d = declared.iloc[-1]
            facts["declared"] = {"situation": d.situation, "date": d.declared_date}
        benefit = cur[cur.category == "child_benefit"]
        if len(benefit):
            facts["childBenefitSince"] = benefit.booking_date.iloc[0]
        recent = tx[tx.account_type.isin(["current", "credit_card"])].tail(8)
        result["personas"][pid] = {
            "customerId": c.customer_id, "firstName": c.first_name, "age": int(c.age), "city": c.city,
            "accounts": accounts, "facts": facts,
            "recentTransactions": [{"date": r.booking_date, "label": r.counterparty_name, "amount": r.amount,
                                    "category": r.category} for r in recent.itertuples()][::-1],
            "transactionCount": int(len(tx)),
        }
    Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {args.out}")
    for pid, p in result["personas"].items():
        print(pid, [(a["kind"], a["balance"]) for a in p["accounts"]], json.dumps(p["facts"], ensure_ascii=False)[:300])


if __name__ == "__main__":
    main()
