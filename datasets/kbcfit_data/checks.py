"""Sanity report on a generated dataset: volumes, balance plausibility, how visible each event is."""
import sqlite3
from pathlib import Path

import pandas as pd

# event -> SQL condition on transactions that is the event's most typical footprint
FOOTPRINT = {
    "birth": "t.category = 'baby'",
    "home_purchase": "t.counterparty_type = 'notary' AND t.amount < -5000",
    "car_purchase": "t.category = 'car_dealer'",
    "job_loss": "t.category = 'unemployment_benefit'",
    "moving_out": "t.category = 'furniture'",
    "wedding": "t.category = 'wedding_services'",
    "retirement": "t.category = 'pension'",
    "inheritance": "t.category = 'inheritance'",
    "child_to_higher_education": "t.category = 'education'",
}


def q(con, sql):
    return pd.read_sql_query(sql, con)


def report(out_dir):
    out = Path(out_dir)
    con = sqlite3.connect(out / "bank.sqlite")
    con.execute(f"ATTACH '{out / 'labels.sqlite'}' AS lab")
    con.execute(f"ATTACH '{out / 'web.sqlite'}' AS web")
    lines = ["# Synthetic dataset report", ""]

    n_cust = q(con, "SELECT COUNT(*) n FROM customers").n[0]
    lines += ["## Volumes", "", "| Table | Rows |", "|---|---|"]
    for db, tables in (("main", ["customers", "accounts", "transactions", "insurance_contracts", "declared_situations",
                                 "monthly_balances", "merchants"]),
                       ("web", ["sessions", "web_events"]),
                       ("lab", ["life_events", "transaction_signals", "web_signals"])):
        for t in tables:
            lines.append(f"| {db if db != 'main' else 'bank'}.{t} | {q(con, f'SELECT COUNT(*) n FROM {db}.{t}').n[0]:,} |")

    lines += ["", "## Money flows (current accounts, per customer and month)", ""]
    flows = q(con, """
        SELECT customer_id, substr(booking_date,1,7) m,
               SUM(CASE WHEN amount > 0 AND category NOT IN ('own_transfer') THEN amount ELSE 0 END) inc,
               SUM(CASE WHEN amount < 0 AND category NOT IN ('own_transfer') THEN -amount ELSE 0 END) out
        FROM transactions WHERE account_type = 'current' GROUP BY 1, 2""")
    per = flows.groupby("customer_id")[["inc", "out"]].mean()
    ratio = (per.out / per.inc.clip(lower=1)).describe(percentiles=[.1, .5, .9])
    lines.append(f"- Median monthly money in: EUR {per.inc.median():,.0f}; out: EUR {per.out.median():,.0f}")
    lines.append(f"- Spending / income ratio: p10 {ratio['10%']:.2f}, median {ratio['50%']:.2f}, p90 {ratio['90%']:.2f}")
    neg = q(con, "SELECT COUNT(DISTINCT customer_id) n FROM transactions WHERE account_type='current' AND balance_after < -1500").n[0]
    lines.append(f"- Customers whose current account ever went below EUR -1,500: {neg} ({neg / n_cust:.1%})")
    txpc = q(con, "SELECT COUNT(*) * 1.0 / COUNT(DISTINCT customer_id) n FROM transactions").n[0]
    lines.append(f"- Transactions per customer over 24 months: {txpc:,.0f}")

    lines += ["", "## Life events (labels)", "", "| Event | Class | Count | Upcoming on END | Declared | strong / medium / weak / none |",
              "|---|---|---|---|---|---|"]
    ev = q(con, "SELECT * FROM lab.life_events")
    for (etype, klass), g in ev.groupby(["event_type", "event_class"]):
        tr = g.trace_level.value_counts()
        lines.append(f"| {etype} | {klass} | {len(g)} | {(g.status == 'upcoming').sum()} | {g.declared_by_customer.sum()} | "
                     f"{tr.get('strong', 0)} / {tr.get('medium', 0)} / {tr.get('weak', 0)} / {tr.get('none', 0)} |")

    lines += ["", "## How visible each event is in the transactions", "",
              "Share of customers showing the event's typical footprint, by trace level, against customers without "
              "that event. The gap is what a detector can learn; the baseline is the noise it has to beat.", "",
              "| Event | Footprint | strong | medium | weak | none | customers without the event |", "|---|---|---|---|---|---|---|"]
    for etype, cond in FOOTPRINT.items():
        has = q(con, f"SELECT DISTINCT t.customer_id FROM transactions t WHERE {cond}")
        has = set(has.customer_id)
        g = ev[(ev.event_type == etype) & (ev.status == "past")]
        if g.empty:
            continue
        cells = []
        for level in ("strong", "medium", "weak", "none"):
            ids = g[g.trace_level == level].customer_id
            cells.append(f"{ids.isin(has).mean():.0%} (n={len(ids)})" if len(ids) else "-")
        without = q(con, "SELECT customer_id FROM customers").customer_id
        without = without[~without.isin(ev[ev.event_type == etype].customer_id)]
        lines.append(f"| {etype} | `{cond.replace('t.', '')}` | {' | '.join(cells)} | {without.isin(has).mean():.1%} |")

    lines += ["", "## Website and app", ""]
    web_users = q(con, "SELECT COUNT(DISTINCT customer_id) n FROM web.sessions").n[0]
    lines.append(f"- Customers with tracked sessions: {web_users:,} ({web_users / n_cust:.0%}); the others refused analytics "
                 "cookies or do not use digital channels")
    spc = q(con, "SELECT COUNT(*) * 1.0 / COUNT(DISTINCT customer_id) n FROM web.sessions").n[0]
    lines.append(f"- Sessions per tracked customer over 24 months: {spc:,.0f}")
    ctr = q(con, """SELECT element, SUM(event_type='offer_impression') imp, SUM(event_type='offer_click') clicks
                    FROM web.web_events WHERE element LIKE 'banner_%' GROUP BY element""")
    ctr["ctr"] = ctr.clicks / ctr.imp
    lines.append(f"- Generic in-app banners (today's app, the same for everyone): {ctr.imp.sum():,} impressions, "
                 f"click-through rate {ctr.clicks.sum() / max(1, ctr.imp.sum()):.2%}")
    top = q(con, """SELECT topic, COUNT(*) n FROM web.web_events WHERE event_type IN ('page_view','search','simulator_submit')
                    AND section='website' GROUP BY topic ORDER BY n DESC LIMIT 8""")
    lines.append("- Most visited website topics: " + ", ".join(f"{r.topic} ({r.n:,})" for r in top.itertuples()))

    lines += ["", "## Demo personas (must match src/lib/data/personas.ts)", "", "| Persona | Account | Balance on END |", "|---|---|---|"]
    demo = q(con, """SELECT c.demo_persona, a.account_type, a.last4, a.balance_end FROM accounts a JOIN customers c USING(customer_id)
                     WHERE c.demo_persona IS NOT NULL ORDER BY c.customer_id, a.account_type""")
    for r in demo.itertuples():
        lines.append(f"| {r.demo_persona} | {r.account_type} ****{r.last4} | EUR {r.balance_end:,.2f} |")
    con.close()
    text = "\n".join(lines) + "\n"
    (out / "report.md").write_text(text)
    print("\n" + text)
