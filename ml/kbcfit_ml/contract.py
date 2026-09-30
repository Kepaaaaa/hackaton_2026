"""The data contract: the only thing a bank has to provide to train and run KBC Fit.

Every source is mapped to these four tables by an adapter: the synthetic generator in
`datasets/` today, a bank's own warehouse tomorrow. The model never reads anything else,
so swapping the source means writing one adapter, not changing the model.

Tables (CSV files in one folder, one row per record):

customers.csv     customer_id, consent_transactions, consent_search
transactions.csv  customer_id, transaction_id, booking_date, amount, category,
                  [counterparty], [country]
web_events.csv    customer_id, timestamp, topic, step, [page], [session_id]
declarations.csv  customer_id, event, declared_date            (optional: what customers told the bank)
balances.csv      customer_id, month, account_type, balance     (optional: month-end balances)
labels.csv        customer_id, event, [event_date]            (training only)

`amount` is signed: negative = money out, positive = money in. Columns in brackets are optional.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

# Spending and income categories the model understands. A bank maps its own categorisation
# (MCC codes for cards, counterparty classification for transfers) onto this list.
CATEGORIES = {
    # everyday spending
    "groceries", "bakery", "drugstore", "restaurant", "cafe_bar", "fast_food", "food_delivery", "clothing",
    "electronics", "diy_garden", "furniture", "discount_store", "marketplace", "books_news", "sports",
    "entertainment", "public_transport", "taxi_mobility", "fuel", "parking", "hair_beauty", "pets", "vet",
    "gifts_flowers", "lottery", "gym", "streaming", "telecom", "utilities", "secondhand", "photo_print",
    # life-moment spending
    "baby", "toys", "childcare", "school", "education", "travel_flight", "travel_lodging", "travel_agency",
    "jewelry", "wedding_services", "legal_notary", "moving_services", "car_dealer", "car_repair", "funeral",
    # recurring transfers and income
    "salary", "pension", "child_benefit", "unemployment_benefit", "rent", "rental_deposit", "mortgage",
    "loan_repayment", "insurance", "tax", "savings_transfer", "transfer_in", "transfer_out", "atm",
    "self_employed_contribution", "other",
    # read by nobody, see FORBIDDEN_CATEGORIES
    "pharmacy", "medical", "dentist", "hospital", "health_reimbursement", "charity",
}

# Special-category data under GDPR art. 9 (health, beliefs). These rows are dropped when the
# data is loaded, before any rule runs, so no signal can ever be built on them.
FORBIDDEN_CATEGORIES = frozenset({"pharmacy", "medical", "dentist", "hospital", "health_reimbursement", "charity"})

# How deep a web visit goes, from browsing to acting. `search` is a site search, `kate` a question
# to the assistant. Everything a bank logs maps onto one of these.
STEPS = ("landing", "article", "help", "app_screen", "product", "life_moment", "search", "kate",
         "tool", "simulator", "form")

TABLES = {
    "customers": {"required": ["customer_id"], "optional": ["consent_transactions", "consent_search"]},
    "transactions": {"required": ["customer_id", "transaction_id", "booking_date", "amount", "category"],
                     "optional": ["counterparty", "country"]},
    "web_events": {"required": ["customer_id", "timestamp", "topic", "step"], "optional": ["page", "session_id"]},
    "declarations": {"required": ["customer_id", "event", "declared_date"], "optional": []},
    "balances": {"required": ["customer_id", "month", "account_type", "balance"], "optional": []},
    "labels": {"required": ["customer_id", "event"], "optional": ["event_date"]},
}


@dataclass
class Tables:
    customers: pd.DataFrame
    transactions: pd.DataFrame
    web_events: pd.DataFrame
    declarations: pd.DataFrame | None = None
    labels: pd.DataFrame | None = None
    balances: pd.DataFrame | None = None


class ContractError(ValueError):
    pass


def _check(name: str, df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in TABLES[name]["required"] if c not in df.columns]
    if missing:
        raise ContractError(f"{name}: missing required columns {missing}")
    keep = TABLES[name]["required"] + [c for c in TABLES[name]["optional"] if c in df.columns]
    return df[keep].copy()


def validate(t: Tables) -> Tables:
    """Check columns and types, apply consent, drop forbidden categories. Returns clean tables."""
    cu = _check("customers", t.customers)
    cu["customer_id"] = cu["customer_id"].astype(str)
    for col in ("consent_transactions", "consent_search"):
        cu[col] = cu[col].astype(bool) if col in cu else True

    tx = _check("transactions", t.transactions)
    tx["customer_id"] = tx["customer_id"].astype(str)
    tx["transaction_id"] = tx["transaction_id"].astype(str)
    tx["booking_date"] = pd.to_datetime(tx["booking_date"]).dt.normalize()
    tx["amount"] = pd.to_numeric(tx["amount"])
    unknown = set(tx["category"].unique()) - CATEGORIES
    if unknown:
        raise ContractError(f"transactions: unknown categories {sorted(unknown)[:10]}; map them in the adapter")
    tx = tx[~tx["category"].isin(FORBIDDEN_CATEGORIES)]

    web = _check("web_events", t.web_events)
    web["customer_id"] = web["customer_id"].astype(str)
    web["timestamp"] = pd.to_datetime(web["timestamp"])
    bad_steps = set(web["step"].unique()) - set(STEPS)
    if bad_steps:
        raise ContractError(f"web_events: unknown steps {sorted(bad_steps)}; allowed: {STEPS}")

    # Consent first: without it the rows are not read at all, not just hidden in the output.
    tx = tx[tx["customer_id"].isin(cu.loc[cu["consent_transactions"], "customer_id"])]
    web = web[web["customer_id"].isin(cu.loc[cu["consent_search"], "customer_id"])]

    decl = None
    if t.declarations is not None:
        decl = _check("declarations", t.declarations)
        decl["customer_id"] = decl["customer_id"].astype(str)
        decl["declared_date"] = pd.to_datetime(decl["declared_date"]).dt.normalize()
        decl = decl[decl["customer_id"].isin(cu.loc[cu["consent_transactions"], "customer_id"])]

    labels = None
    if t.labels is not None:
        labels = _check("labels", t.labels)
        labels["customer_id"] = labels["customer_id"].astype(str)
        if "event_date" in labels:
            labels["event_date"] = pd.to_datetime(labels["event_date"])
    balances = None
    if t.balances is not None:
        balances = _check("balances", t.balances)
        balances["customer_id"] = balances["customer_id"].astype(str)
        balances = balances[balances["customer_id"].isin(cu.loc[cu["consent_transactions"], "customer_id"])]
    return Tables(cu.reset_index(drop=True), tx.reset_index(drop=True), web.reset_index(drop=True),
                  None if decl is None else decl.reset_index(drop=True), labels, balances)


def load(folder: str | Path, with_labels: bool = False) -> Tables:
    folder = Path(folder)
    read = lambda name: pd.read_csv(folder / f"{name}.csv", low_memory=False)  # noqa: E731
    labels = read("labels") if with_labels and (folder / "labels.csv").exists() else None
    if with_labels and labels is None:
        raise ContractError(f"{folder}/labels.csv not found: training needs labels")
    optional = lambda name: read(name) if (folder / f"{name}.csv").exists() else None  # noqa: E731
    return validate(Tables(read("customers"), read("transactions"), read("web_events"), optional("declarations"),
                           labels, optional("balances")))
