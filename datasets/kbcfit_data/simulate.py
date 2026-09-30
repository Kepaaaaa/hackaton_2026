"""Simulate one customer end to end and return the rows of every table (bank, web, labels)."""
import numpy as np
import pandas as pd

from . import reference as R
from .bank import CustomerSim
from .calendar import END, IS_BUSINESS, MONTHS, NDAYS, START, to_date
from .customers import DEMO_PERSONAS, demo_customer, generate_customer
from .events import sample_events, to_label_rows
from .merchants import registry
from .web import WebSim

PRODUCT_NAMES = {"current": "KBC Current Account", "savings": "Savings Account", "pension_savings": "Pension Savings Fund",
                 "long_term_savings": "Long-term Savings (branch 21)", "investment_plan": "Investment Plan",
                 "credit_card": "KBC Credit Card", "home_loan": "Home Loan", "car_loan": "Car Loan",
                 "child_savings": "Savings Account for my Child", "rental_guarantee": "Rental Guarantee Account"}
CARD_CHANNELS = {"card_pos", "card_contactless", "card_online", "mobile_payment", "credit_card"}

_NEXT_BUSINESS = np.arange(NDAYS + 10)
for _i in range(NDAYS - 1, -1, -1):
    _NEXT_BUSINESS[_i] = _i if IS_BUSINESS[_i] else _NEXT_BUSINESS[_i + 1] if _i + 1 < NDAYS else _i
_DAY0 = np.datetime64(START.isoformat())


def iso_ts(seconds):
    return (np.datetime64(f"{START.isoformat()}T00:00:00") + np.asarray(seconds).astype("timedelta64[s]")).astype(str)


def iso_day(days):
    return (_DAY0 + np.asarray(days).astype("timedelta64[D]")).astype(str)


def simulate_one(idx: int, seed: int) -> dict:
    rng = np.random.default_rng([seed, idx])
    if idx <= len(DEMO_PERSONAS):
        p = demo_customer(idx, DEMO_PERSONAS[idx - 1], rng)
    else:
        p = generate_customer(idx, rng)
    events = sample_events(p, rng)
    for k, e in enumerate(events):
        e["event_id"] = idx * 100 + k + 1
        if e["event_type"] in ("first_job", "job_loss", "new_job", "retirement") and e["trace"] == "none":
            e["trace"] = "weak"            # the salary itself is always visible to the bank
    sim = CustomerSim(p, events, rng)
    out = sim.run()
    c = sim.L.c
    order = out["order"]
    n = len(order)
    cid = p["customer_id"]

    # ---------------------------------------------------------------- accounts
    acc_ids = {}
    acc_rows = []
    for k, (key, a) in enumerate(sorted(sim.accounts.items(), key=lambda kv: kv[1]["opened_day"])):
        acc_id = f"A{idx:07d}{k:02d}"
        acc_ids[key] = acc_id
        opened = max(a["opened_day"], (p["customer_since"] - START).days)
        acc_rows.append({
            "account_id": acc_id, "customer_id": cid, "account_type": key,
            "product_name": a.get("product_name") or PRODUCT_NAMES.get(key, key),
            "provider": "KBC", "iban_masked": f"BE** **** **** {a['last4']}" if key not in ("home_loan", "car_loan") else None,
            "last4": a["last4"], "opened_date": to_date(opened).isoformat(),
            "balance_start": round(a["opening"], 2) if opened < 0 else 0.0,
            "balance_end": out["final"].get(key, round(a["opening"], 2)), "currency": "EUR",
        })

    # ---------------------------------------------------------------- transactions
    acct = np.array(c["account"], dtype=object)[order]
    day = np.array(c["day"], dtype=np.int64)[order]
    ts = out["ts"][order]
    amount = np.array(c["amount"])[order]
    channel = np.array(c["channel"], dtype=object)[order]
    category = np.array(c["category"], dtype=object)[order]
    merchant = np.array(c["merchant_id"], dtype=np.int64)[order]
    tx_id = idx * 100_000 + np.arange(1, n + 1)
    is_card = np.isin(channel, list(CARD_CHANNELS))
    booking = np.where(is_card, _NEXT_BUSINESS[np.minimum(day + 1, NDAYS - 1)], day)
    M = registry()
    mcc = np.array([M.rows[m - 1]["mcc"] if m > 0 else R.CATEGORY_MCC.get(cat, 0) for m, cat in zip(merchant, category)])
    tx = pd.DataFrame({
        "transaction_id": tx_id, "account_id": [acc_ids[a] for a in acct], "customer_id": cid,
        "account_type": acct, "booking_date": iso_day(booking), "transaction_ts": iso_ts(ts), "amount": amount,
        "direction": np.where(amount > 0, "credit", "debit"), "currency": "EUR",
        "balance_after": out["balances"][order], "category": category, "mcc": np.where(mcc > 0, mcc, None),
        "channel": channel, "counterparty_name": np.array(c["counterparty"], dtype=object)[order],
        "counterparty_type": np.array(c["cp_type"], dtype=object)[order],
        "merchant_id": np.where(merchant > 0, merchant, None),
        "merchant_city": np.array(c["city"], dtype=object)[order],
        "merchant_country": np.array(c["country"], dtype=object)[order],
        "description": np.array(c["description"], dtype=object)[order],
        "is_recurring": np.array(c["recurring"])[order],
        "original_currency": np.array(c["orig_currency"], dtype=object)[order],
        "original_amount": np.array(c["orig_amount"], dtype=object)[order],
    })
    ev_col = np.array(c["event_id"], dtype=np.int64)[order]
    sig_col = np.array(c["signal"], dtype=object)[order]
    linked = ev_col > 0
    tx_signals = pd.DataFrame({"event_id": ev_col[linked], "transaction_id": tx_id[linked],
                               "signal": sig_col[linked]})

    # monthly balances (month-end) per account
    mb_rows = []
    for key, acc_id in acc_ids.items():
        mask = acct == key
        d_k, b_k = day[mask], out["balances"][order][mask]
        opening = sim.accounts[key]["opening"]
        opened = sim.accounts[key]["opened_day"]
        for (y, m, first, last) in MONTHS:
            if last < opened:
                continue
            j = np.searchsorted(d_k, last, side="right") - 1
            mb_rows.append({"account_id": acc_id, "customer_id": cid, "month": f"{y}-{m:02d}",
                            "balance_end_of_month": round(float(b_k[j]) if j >= 0 else opening, 2)})

    # ---------------------------------------------------------------- inputs for the web simulation
    cur = acct == "current"
    income_days = sorted(set(day[cur & np.isin(category, ["salary", "pension", "unemployment_benefit"])].tolist()))
    tr_mask = cur & ((channel == "instant_transfer_out") | ((channel == "transfer_out") & ~tx["is_recurring"].to_numpy()))
    transfers = list(zip(day[tr_mask].tolist(), (ts[tr_mask] % 86400).tolist(), tx_id[tr_mask].tolist()))
    spend_mask = cur & (amount < 0) & (category != "own_transfer")
    idle = []
    cur_bal = out["balances"][order][cur]
    cur_day = day[cur]
    for (y, m, first, last) in MONTHS:
        j = np.searchsorted(cur_day, last, side="right") - 1
        spent = -amount[spend_mask & (day >= first) & (day <= last)].sum()
        idle.append((last, float(cur_bal[j]) if j >= 0 else 0.0, float(spent)))
    bank_out = {"income_days": income_days, "transfers": transfers, "idle_months": idle,
                "trips": getattr(sim, "trips", [])}
    web = WebSim(p, sim, bank_out, rng, idx)
    sessions, wevents, wlinks = web.run()

    # ---------------------------------------------------------------- customer (what the bank knows)
    t = p["traits"]
    kids_known = len(p["children"]) + sum(1 for d, s, ev in sim.declared if s == "expecting_a_child"
                                          and next(e for e in events if e["event_id"] == ev)["day"] < NDAYS)
    customer = {
        "customer_id": cid, "first_name": p["first_name"], "last_name": p["last_name"], "gender": p["gender"],
        "birth_date": p["birth_date"].isoformat(), "age": int((END - p["birth_date"]).days // 365.25),
        "language": p["language"], "city": p["city"], "postcode": p["postcode"], "province": p["province"],
        "region": p["region"], "customer_since": p["customer_since"].isoformat(),
        "employment_status_kyc": p["employment"], "marital_status_kyc": p["marital_status"],
        "housing_status_kyc": p["housing"], "children_known": kids_known,
        "risk_profile": p["risk_profile"], "consent_personalisation": p["consent_personalisation"],
        "consent_analytics": p["consent_analytics"], "consent_marketing": p["consent_marketing"],
        "has_mobile_app": t["digital_affinity"] > 0, "demo_persona": p["demo_persona"],
    }
    contracts = [{
        "contract_id": f"K{idx:07d}{k:02d}", "customer_id": cid, "product_type": ct["product_type"],
        "insurer": "KBC Insurance", "start_date": to_date(ct["start_day"]).isoformat(),
        "end_date": to_date(ct["end_day"]).isoformat() if ct["end_day"] < NDAYS else None,
        "yearly_premium": ct["yearly_premium"], "premium_frequency": ct["frequency"],
    } for k, ct in enumerate(sim.contracts)]
    declared = [{"customer_id": cid, "situation": s, "declared_date": to_date(d).isoformat(), "channel": "mobile_app"}
                for d, s, ev in sim.declared if d is not None and 0 <= d < NDAYS]

    # ---------------------------------------------------------------- ground truth (labels only)
    last_job = sim.current_job(NDAYS - 1)
    truth = {
        "customer_id": cid, "archetype": p["archetype"], "employment_at_end": {
            "salary": "employee", "civil": "civil_servant", "self": "self_employed", "student_job": "student",
            "unemployment": "unemployed", "pension": "retired"}.get(last_job["kind"] if last_job else "", "unknown"),
        "net_income_at_end": last_job["net"] if last_job else 0.0,
        "housing_at_end": sim.housing_at(NDAYS - 1)["kind"],
        "has_partner_at_end": sim.partner_from <= NDAYS - 1 < sim.partner_to,
        "children_at_end": sum(1 for b, _, _ in sim.kids if b < NDAYS), "household_arrangement": sim.arrangement,
        "has_car_at_end": sim.car_from < NDAYS, **{f"trait_{k}": v for k, v in t.items()},
    }
    external = [{"customer_id": cid, "product_type": k, "provider": v} for k, v in sim.external]
    return {
        "customers": [customer], "accounts": acc_rows, "transactions": tx, "insurance_contracts": contracts,
        "declared_situations": declared, "monthly_balances": mb_rows,
        "sessions": sessions, "web_events": wevents,
        "life_events": to_label_rows(events), "transaction_signals": tx_signals,
        "web_signals": wlinks, "customer_truth": [truth], "external_products": external,
    }
