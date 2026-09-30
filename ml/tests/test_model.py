import json

import numpy as np
import pandas as pd
import pytest

from kbcfit_ml import contract, model
from kbcfit_ml.__main__ import main
from kbcfit_ml.catalog import EVENTS_BY_ID, SIGNALS
from kbcfit_ml.report import compose
from kbcfit_ml.signals import evaluate, prepare

AS_OF = "2026-09-30"


class Builder:
    """Tiny contract tables written by hand, one customer at a time."""

    def __init__(self):
        self.cu, self.tx, self.web, self.decl, self.labels = [], [], [], [], []

    def customer(self, cid, consent_tx=True, consent_search=True, since="2024-10-01"):
        self.cu.append({"customer_id": cid, "consent_transactions": consent_tx, "consent_search": consent_search})
        # a year and a half of groceries so every customer has history
        for d in pd.date_range(since, AS_OF, freq="14D"):
            self.pay(cid, d, -60, "groceries", "Colruyt")
        return self

    def pay(self, cid, date, amount, category, counterparty="", country="BE"):
        self.tx.append({"customer_id": cid, "transaction_id": f"T{len(self.tx)}", "booking_date": str(date)[:10],
                        "amount": amount, "category": category, "counterparty": counterparty, "country": country})

    def visit(self, cid, date, topic, step="product", page="p"):
        self.web.append({"customer_id": cid, "timestamp": f"{str(date)[:10]}T12:00:00", "topic": topic,
                         "step": step, "page": page, "session_id": f"{cid}-{str(date)[:10]}"})

    def tables(self) -> contract.Tables:
        web = pd.DataFrame(self.web, columns=["customer_id", "timestamp", "topic", "step", "page", "session_id"])
        decl = pd.DataFrame(self.decl, columns=["customer_id", "event", "declared_date"])
        labels = pd.DataFrame(self.labels, columns=["customer_id", "event", "event_date"])
        return contract.validate(contract.Tables(pd.DataFrame(self.cu), pd.DataFrame(self.tx), web, decl, labels))


def one(b: Builder, cid: str, m=None) -> dict:
    return next(compose(prepare(b.tables()), m or model.untrained(), AS_OF, only=[cid]))


def test_catalog_never_reads_health_data():
    for s in SIGNALS.values():
        assert not s.rule.categories & contract.FORBIDDEN_CATEGORIES


def test_forbidden_rows_are_dropped_on_load():
    b = Builder().customer("A")
    b.pay("A", "2026-09-01", -30, "pharmacy", "Multipharma")
    t = b.tables()
    assert "pharmacy" not in set(t.transactions["category"])


def test_unknown_category_is_rejected():
    b = Builder().customer("A")
    b.pay("A", "2026-09-01", -30, "crypto")
    with pytest.raises(contract.ContractError):
        b.tables()


def test_no_consent_means_nothing_is_read():
    b = Builder().customer("A", consent_tx=False, consent_search=False)
    b.pay("A", "2026-09-01", -15_000, "car_dealer", "Garage Peeters")
    b.visit("A", "2026-09-20", "car_loan", "simulator")
    doc = one(b, "A")
    assert doc["consent"] == {"transactions": False, "search": False}
    assert doc["transactions"] == [] and doc["searches"] == []


def test_onset_needs_something_new():
    b = Builder().customer("NEW").customer("OLD")
    for d in pd.date_range("2026-07-01", AS_OF, freq="MS"):
        b.pay("NEW", d, 180, "child_benefit", "FONS")
    for d in pd.date_range("2024-10-01", AS_OF, freq="MS"):
        b.pay("OLD", d, 180, "child_benefit", "FONS")
    v = evaluate(prepare(b.tables()), AS_OF)["child_benefit_started"]
    assert v.fired.tolist() == [True, False]


def test_point_in_time_ignores_the_future():
    b = Builder().customer("A")
    b.pay("A", "2026-10-15", -20_000, "car_dealer", "Garage Peeters")
    assert not evaluate(prepare(b.tables()), AS_OF)["car_dealer_payment"].fired[0]


def test_confidence_is_the_sum_of_listed_weights_and_sensitive_needs_confirmation():
    b = Builder().customer("A").customer("B")
    for cid in ("A", "B"):
        for d in ("2026-08-02", "2026-09-05"):
            b.pay(cid, d, -120, "baby", "Dreambaby")
        for d in pd.date_range("2026-07-01", AS_OF, freq="MS"):
            b.pay(cid, d, 180, "child_benefit", "FONS")
    b.decl.append({"customer_id": "B", "event": "birth", "declared_date": "2026-08-05"})
    a, bb = one(b, "A"), one(b, "B")
    for doc in (a, bb):
        birth = doc["transactions"][0]
        assert birth["event"] == "birth"
        assert birth["confidence"] == round(min(1, sum(s["weight"] for s in birth["signals"])), 2)
        assert all(s["evidence"] for s in birth["signals"] if s["source"] == "transactions")
    assert a["transactions"][0]["status"] == "ask_customer"
    assert bb["transactions"][0]["status"] == "ready"
    assert {s["source"] for s in bb["transactions"][0]["signals"]} == {"transactions", "declared"}


def test_searches_rank_simulators_above_page_views_and_fade():
    b = Builder().customer("A")
    for d in ("2026-09-26", "2026-09-28"):
        b.visit("A", d, "home_loan", "simulator", "web_home_loan_sim")
    b.visit("A", "2026-09-27", "investing", "article", "news_markets")
    b.visit("A", "2026-07-10", "car_loan", "simulator", "web_car_loan_sim")   # old: faded
    b.visit("A", "2026-09-20", "daily_banking", "app_screen")                # not a product topic
    topics = [s["topic"] for s in one(b, "A")["searches"]]
    assert topics[0] == "home_loan"
    assert "daily_banking" not in topics
    home = one(b, "A")["searches"][0]
    assert home["deepest_step"] == "simulator" and home["sessions"] == 2


def _population(n=600, seed=1) -> Builder:
    """Car buyers pay a dealer; a random third of everyone reads about car loans (uninformative)."""
    rng = np.random.default_rng(seed)
    b = Builder()
    for i in range(n):
        cid = f"C{i:04d}"
        b.customer(cid, since="2025-06-01")
        buyer = rng.random() < 0.3
        if buyer:
            b.labels.append({"customer_id": cid, "event": "car_purchase", "event_date": "2026-09-10"})
            if rng.random() < 0.85:
                b.pay(cid, "2026-09-10", -float(rng.uniform(8_000, 30_000)), "car_dealer", "Garage Maes")
        elif rng.random() < 0.05:
            b.pay(cid, "2026-09-12", -2_500, "car_dealer", "Garage Maes")   # a big repair billed by a dealer
        if rng.random() < 0.33:
            b.visit(cid, "2026-09-15", "car_loan", "product")
    return b


def test_training_learns_which_signal_matters():
    b = _population()
    t = b.tables()
    m = model.train(prepare(t), t.labels, [AS_OF], "test")
    car = m["events"]["car_purchase"]
    assert car["trained"]
    assert car["weights"]["car_dealer_payment"] > 0.6
    assert car["weights"]["car_loan_pages"] < 0.2
    assert car["test"]["learned"]["auc"] >= car["test"]["expert_priors"]["auc"] - 0.01
    assert not m["events"]["travel"]["trained"]          # no labels: expert priors are kept
    assert m["events"]["travel"]["weights"] == EVENTS_BY_ID["travel"].priors


def test_cli_train_then_predict(tmp_path):
    b = _population(300)
    folder = tmp_path / "data"
    folder.mkdir()
    pd.DataFrame(b.cu).to_csv(folder / "customers.csv", index=False)
    pd.DataFrame(b.tx).to_csv(folder / "transactions.csv", index=False)
    pd.DataFrame(b.web).to_csv(folder / "web_events.csv", index=False)
    pd.DataFrame(b.labels).to_csv(folder / "labels.csv", index=False)
    out = tmp_path / "model.json"
    main(["train", "--data", str(folder), "--out", str(out), "--as-of", AS_OF])
    assert (tmp_path / "model_card.md").read_text().startswith("# KBC Fit signal model")
    preds = tmp_path / "preds.jsonl"
    main(["predict", "--data", str(folder), "--model", str(out), "--out", str(preds)])
    docs = [json.loads(line) for line in preds.read_text().splitlines()]
    assert len(docs) == 300
    assert {"customer_id", "as_of", "model", "consent", "transactions", "searches"} <= set(docs[0])
