"""Adapter: the synthetic generator (datasets/kbcfit_data) -> the data contract.

This is the file a bank replaces. It keeps only what a bank can actually observe:

- The generator's answer-key columns (`event_id`, `signal`, the web-event links) are dropped,
  so the model cannot cheat.
- Categories that give the answer away are replaced by what a categoriser would see:
  a transfer labelled `home_purchase` or `inheritance` becomes a payment to or from a notary.
- Product outcomes are not signals: loan disbursements and online applications are removed,
  because a bank already knows about a loan it granted.

    python -m kbcfit_ml.adapters.synthetic --src ../datasets/output --out data/synthetic
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ..contract import CATEGORIES

START = pd.Timestamp("2024-10-01")   # day 0 of the generator (datasets/kbcfit_data/calendar.py)

# generator category -> contract category (identical names pass through)
CATEGORY_MAP = {
    "home_purchase": "legal_notary", "deed_costs": "legal_notary", "notary_deposit": "legal_notary",
    "notary": "legal_notary", "legal": "legal_notary", "inheritance": "legal_notary",
    "student_room": "rent", "student_room_rent": "rent",
    "mortgage_repayment": "mortgage", "home_loan": "mortgage",
    "car_loan": "loan_repayment", "car_payment": "car_dealer",
    "energy": "utilities", "water": "utilities", "utility": "utilities",
    "subscription": "streaming", "road_tax": "tax", "social_contributions": "self_employed_contribution",
    "lump_sum": "insurance", "property_tax": "tax",
    # health data (GDPR art. 9): mutuality premiums and refunds, maternity benefit
    "health_refund": "health_reimbursement", "health_insurance": "health_reimbursement",
    "maternity_benefit": "health_reimbursement",
    "home_improvement": "diy_garden", "contractor_invoice": "diy_garden",
    "savings": "savings_transfer", "birth_allowance": "child_benefit",
    "fee": "other", "bank_fees": "other", "interest": "other", "tickets": "entertainment",
}
# money between people, or income that is not a salary: only the direction is kept
PERSON_TO_PERSON = {"household_contribution", "partner_contribution", "family_support", "allowance_to_child", "p2p",
                    "gift", "gift_received", "expense_refund", "business_income"}
DROP_CATEGORIES = {"own_transfer", "card_settlement"}      # money moving between the customer's own accounts
KEEP_ACCOUNTS = {"current", "credit_card"}                  # where everyday flows are booked
OUTCOME_EVENTS = {"form_start", "application_submitted"}    # applying for a product is an outcome
NOT_AN_ACTION = {"offer_impression"}                        # a banner shown, not something the customer did

# what customers declare in the app ("my situation") -> contract event
SITUATION_TO_EVENT = {"expecting_a_child": "birth", "new_child": "birth", "buying_a_home": "home_purchase", "moving": "moving_out",
                      "living_together": "cohabitation", "getting_married": "wedding", "lost_job": "job_loss",
                      "new_job": "new_job", "separating": "separation", "retiring": "retirement"}
NON_PRODUCT_TOPICS = {"appointment", "application"}         # attributed to the topic browsed just before


def _timestamps(col: pd.Series) -> pd.Series:
    if np.issubdtype(col.dtype, np.number):          # seconds since day 0
        return START + pd.to_timedelta(col, unit="s")
    return pd.to_datetime(col)


def map_transactions(tx: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    tx = tx.copy()
    cp = tx["counterparty_name"].astype(str)
    is_deposit = (tx["category"] == "own_transfer") & cp.str.contains("rental guarantee", case=False)
    tx.loc[is_deposit & (tx["amount"] < 0), "category"] = "rental_deposit"
    tx = tx[tx["account_type"].isin(KEEP_ACCOUNTS)]
    tx = tx[(tx["channel"] != "loan_disbursement") & ~tx["category"].isin(DROP_CATEGORIES)]

    cat = tx["category"].map(lambda c: CATEGORY_MAP.get(c, c))
    cat = cat.where(tx["counterparty_type"] != "notary", "legal_notary")
    p2p = tx["category"].isin(PERSON_TO_PERSON)
    cat = cat.where(~p2p, np.where(tx["amount"] > 0, "transfer_in", "transfer_out"))
    unknown = ~cat.isin(CATEGORIES)
    report = cat[unknown].value_counts().to_dict()
    cat = cat.where(~unknown, "other")
    out = pd.DataFrame({
        "customer_id": tx["customer_id"].astype(str),
        "transaction_id": tx["transaction_id"].astype(str),
        "booking_date": pd.to_datetime(tx["booking_date"]).dt.strftime("%Y-%m-%d"),
        "amount": tx["amount"],
        "category": cat,
        "counterparty": tx["counterparty_name"],
        "country": tx["merchant_country"].fillna("BE"),
    })
    return out, report


def map_web(web: pd.DataFrame) -> pd.DataFrame:
    web = web.copy()
    ts = web["timestamp"] if "timestamp" in web else web["ts"]
    web["timestamp"] = _timestamps(ts)
    web = web.sort_values(["customer_id", "session_id", "timestamp"])
    if "event_type" in web:
        web = web[~web["event_type"].isin(OUTCOME_EVENTS) | (web["page_id"] == "appointment_book")]
        web = web[~((web["event_type"] == "form_submit") & (web["page_id"] == "app_situation"))]
        web = web[~web["event_type"].isin(NOT_AN_ACTION)]
    topic = web["topic"].where(~web["topic"].isin(NON_PRODUCT_TOPICS))
    web["topic"] = topic.groupby(web["session_id"]).ffill().fillna("general")
    return pd.DataFrame({
        "customer_id": web["customer_id"].astype(str),
        "timestamp": web["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "topic": web["topic"],
        "step": web["step"].fillna("app_screen"),
        "page": web["page_id"],
        "session_id": web["session_id"].astype(str),
    })


def map_labels(life_events: pd.DataFrame) -> pd.DataFrame:
    """Ground truth -> labels.csv. Decoys (grandparents, business trips...) are not labels."""
    life = life_events[life_events["event_class"] == "life_event"]
    return pd.DataFrame({"customer_id": life["customer_id"], "event": life["event_type"],
                         "event_date": life["event_date"]})


def map_declarations(declared: pd.DataFrame) -> pd.DataFrame:
    """What customers told the bank in the app: observable, so an input, not a label."""
    event = declared["situation"].map(SITUATION_TO_EVENT)
    d = declared[event.notna()]
    return pd.DataFrame({"customer_id": d["customer_id"], "event": event[event.notna()],
                         "declared_date": d["declared_date"]})


def _bool(col: pd.Series) -> pd.Series:
    return col.astype(str).str.lower().isin({"1", "true"})      # SQLite stores booleans as 0/1


def map_customers(cu: pd.DataFrame) -> pd.DataFrame:
    pers, analytics = _bool(cu["consent_personalisation"]), _bool(cu["consent_analytics"])
    return pd.DataFrame({"customer_id": cu["customer_id"].astype(str), "consent_transactions": pers,
                         "consent_search": pers & analytics})


def _query(db: Path, sql: str) -> pd.DataFrame:
    with sqlite3.connect(db) as con:
        return pd.read_sql_query(sql, con)


def convert(src: Path, out: Path) -> None:
    """Read the generator's SQLite output (bank / web / labels) and write the contract CSV folder."""
    out.mkdir(parents=True, exist_ok=True)
    bank, web, labels = src / "bank.sqlite", src / "web.sqlite", src / "labels.sqlite"
    for f in (bank, web, labels):
        if not f.exists():
            raise FileNotFoundError(f"{f} not found: run `python -m kbcfit_data` in datasets/ first")

    cu = map_customers(_query(bank, "SELECT customer_id, consent_personalisation, consent_analytics FROM customers"))
    cu.to_csv(out / "customers.csv", index=False)

    tx = _query(bank, "SELECT transaction_id, customer_id, account_type, booking_date, amount, category, channel, "
                      "counterparty_name, counterparty_type, merchant_country FROM transactions")
    tx, unknown = map_transactions(tx)
    tx.to_csv(out / "transactions.csv", index=False)
    if unknown:
        print(f"categories mapped to 'other': {unknown}", file=sys.stderr)

    we = _query(web, "SELECT customer_id, session_id, event_ts AS timestamp, event_type, page_id, topic, step "
                     "FROM web_events")
    map_web(we).to_csv(out / "web_events.csv", index=False)

    map_declarations(_query(bank, "SELECT customer_id, situation, declared_date FROM declared_situations")) \
        .to_csv(out / "declarations.csv", index=False)
    map_labels(_query(labels, "SELECT customer_id, event_type, event_class, event_date FROM life_events")) \
        .to_csv(out / "labels.csv", index=False)
    _query(bank, "SELECT b.customer_id, b.month, a.account_type, b.balance_end_of_month AS balance "
                 "FROM monthly_balances b JOIN accounts a USING (account_id) "
                 "WHERE a.account_type IN ('current', 'savings')").to_csv(out / "balances.csv", index=False)
    print(f"{len(cu):,} customers, {len(tx):,} transactions, {len(we):,} web events -> {out}", file=sys.stderr)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default="../datasets/output", help="folder with bank/web/labels.sqlite")
    ap.add_argument("--out", default="data/synthetic")
    a = ap.parse_args(argv)
    convert(Path(a.src), Path(a.out))


if __name__ == "__main__":
    main()
