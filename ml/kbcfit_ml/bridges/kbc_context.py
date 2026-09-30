"""Bridge to the KBC Context backend (branch `Mathias`, folder backend/): run its pipeline on the
synthetic customers, score its moments against the ground truth, and learn its moment weights.

The backend's moments are additive, like our events: confidence = min(1, Σ weight × strength).
So the same training code can learn its `MomentRule.signal_weights` from outcomes, and the
learned rules are injected with `ContextEngine(rules=...)`. Not a line of the backend changes.
What is never learned: TTLs, and the `requires_any` cap that keeps NEW_PARENT at 0.35 until the
customer declares it. Those are policy, not statistics.

    python -m kbcfit_ml.bridges.kbc_context learn --backend ../backend --data data/synthetic
    python -m kbcfit_ml.bridges.kbc_context run   --backend ../backend --data data/synthetic --customer C0000002
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .. import contract
from ..catalog import EVENTS_BY_ID
from ..model import MIN_POSITIVES, TEST_SHARE, _metrics, fit_weights, score
from ..signals import Prepared, day_number, labels_at, prepare

HISTORY_DAYS = 400      # longest backend TTL (365) plus the salary-pattern lookback

# our life event -> backend moment
EVENT_TO_MOMENT = {"birth": "NEW_PARENT", "first_job": "FIRST_SALARY", "retirement": "RETIREMENT_TRANSITION",
                   "car_purchase": "CAR_PROJECT", "home_purchase": "HOME_BUYING", "inheritance": "LARGE_CASH_INFLOW",
                   "travel": "TRAVEL"}

# contract category -> backend TransactionCategory
CATEGORY = {
    "salary": "salary", "pension": "pension", "rent": "rent", "mortgage": "mortgage_payment",
    "loan_repayment": "loan_repayment", "groceries": "groceries", "bakery": "groceries", "utilities": "utilities",
    "telecom": "utilities", "public_transport": "transport", "taxi_mobility": "transport", "fuel": "transport",
    "parking": "transport", "restaurant": "restaurants", "cafe_bar": "restaurants", "fast_food": "restaurants",
    "food_delivery": "restaurants", "entertainment": "leisure", "sports": "leisure", "streaming": "leisure",
    "gym": "leisure", "books_news": "leisure", "travel_flight": "airline", "travel_lodging": "hotel",
    "travel_agency": "hotel", "car_dealer": "automotive", "car_repair": "automotive", "childcare": "childcare",
    "baby": "baby_supplies", "insurance": "insurance_premium", "savings_transfer": "savings_transfer",
}
INCOME_OTHER = {"child_benefit", "unemployment_benefit", "transfer_in", "legal_notary", "insurance", "other"}
# contract web topic -> backend KbcPage, SimulationType, and a search text its keyword rules understand
PAGE = {"car_loan": "car_loan", "car_insurance": "car_insurance", "home_loan": "mortgage",
        "home_insurance": "home_insurance", "travel": "travel_insurance", "cards": "card_abroad_settings",
        "investing": "investment_info", "pension_savings": "pension_savings", "child_savings": "child_savings",
        "baby_family": "family_insurance", "budgeting": "budgeting_tools", "retirement": "retirement_planning",
        "savings": "savings_accounts"}
SIMULATION = {"car_loan": "car_loan", "home_loan": "mortgage", "pension_savings": "pension_savings",
              "retirement": "pension_savings", "investing": "investment_plan", "savings": "savings_plan",
              "child_savings": "savings_plan"}
SEARCH_TEXT = {"car_loan": "car loan", "home_loan": "home mortgage", "investing": "invest in funds",
               "pension_savings": "pension savings", "savings": "savings account", "travel": "travel insurance"}
DECLARED = {"birth": "expecting_child", "retirement": "retiring", "moving_out": "moving", "new_job": "new_job"}


def import_backend(path: str | Path):
    """Put the backend on sys.path and return the modules the bridge needs."""
    root = Path(path).resolve()
    if not (root / "app" / "engines").is_dir():
        raise SystemExit(f"{root} is not the KBC Context backend (expected app/engines/ inside)")
    sys.path.insert(0, str(root))
    from app.engines import context_engine as ce
    from app.models import customer as cm
    from app.models import event as em
    from app.rules import moments as mr
    from app.services import personalization_service as ps
    return ce, cm, em, mr, ps


class Bridge:
    def __init__(self, backend: str | Path, tables: contract.Tables):
        self.ce, self.cm, self.em, self.mr, self.ps = import_backend(backend)
        self.t = tables
        self.p: Prepared = prepare(tables)
        self.cat_name = np.array(list(self.p.cat_code), dtype=object)
        self.topic_name = np.array(list(self.p.topic_code), dtype=object)
        self.step_name = np.array(list(self.p.step_code), dtype=object)
        self.web_order = np.argsort(self.p.web_c, kind="stable")
        self.web_start = np.searchsorted(self.p.web_c[self.web_order], np.arange(self.p.n + 1))
        self.tx_start = np.searchsorted(self.p.tx_c, np.arange(self.p.n + 1))
        self.balances = self._balances(tables.balances)

    @staticmethod
    def _balances(b: pd.DataFrame | None) -> dict:
        if b is None or b.empty:
            return {}
        b = b.sort_values("month")
        return {(c, t): (g["month"].to_numpy(), g["balance"].to_numpy()) for (c, t), g in b.groupby(
            ["customer_id", "account_type"])}

    def _balance_at(self, cid: str, kind: str, as_of: pd.Timestamp) -> float:
        months, values = self.balances.get((cid, kind), (np.array([]), np.array([])))
        k = np.searchsorted(months, as_of.strftime("%Y-%m"), side="right") - 1
        return float(values[k]) if k >= 0 else (1500.0 if kind == "current" else 0.0)

    @staticmethod
    def backend_id(cid: str) -> str:
        return cid.lower()             # backend ids match ^[a-z][a-z0-9_-]{1,31}$

    def customer(self, i: int, as_of: pd.Timestamp):
        cm, cid = self.cm, str(self.p.customer_ids[i])
        profile = cm.CustomerProfile(
            life_stage="established", employment=cm.Employment(status="employed", type="salaried"),
            income_stage="established", housing=cm.Housing(status="tenant", mortgage=False),
            family=cm.Family(status="single", children=0),
            financial_profile=cm.FinancialProfile(savings_level="medium", income_stability="stable",
                                                  financial_maturity="intermediate"))
        accounts = [cm.Account(id=f"{cid}-{k}", type=k, label=k.title(), masked_number="•••• 0000",
                               balance=round(self._balance_at(cid, k, as_of), 2)) for k in ("current", "savings")]
        return cm.Customer(id=self.backend_id(cid), first_name="Customer", age=40, profile=profile, accounts=accounts,
                           products=[], consent=cm.Consent(personalization=bool(self.p.consent_tx[i])))

    def events(self, i: int, as_of: pd.Timestamp) -> list:
        em, p, bid = self.em, self.p, self.backend_id(str(self.p.customer_ids[i]))
        a = day_number(as_of)
        out = []
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        when = lambda day, hour=12: epoch + timedelta(days=int(day), hours=hour)  # noqa: E731
        lo, hi = self.tx_start[i], self.tx_start[i + 1]
        for r in range(lo, hi):
            d = p.tx_day[r]
            if not a - HISTORY_DAYS <= d <= a:
                continue
            amt, cat = p.tx_amt[r], self.cat_name[p.tx_cat[r]]
            if amt == 0:
                continue
            category = CATEGORY.get(cat) or ("other_income" if amt > 0 and cat in INCOME_OTHER else "other")
            out.append(em.TransactionEvent(
                id=f"t{p.tx_id[r]}", customer_id=bid, timestamp=when(d), origin="seed",
                data=em.TransactionData(direction="in" if amt > 0 else "out", amount=min(abs(amt), 1_000_000),
                                        category=category, merchant=(p.tx_counterparty[r] or "Unknown")[:80],
                                        recurring=cat in ("salary", "pension", "rent", "mortgage"))))
        for k, r in enumerate(self.web_order[self.web_start[i]:self.web_start[i + 1]]):
            d = p.web_day[r]
            if not a - HISTORY_DAYS <= d <= a:
                continue
            topic, step = self.topic_name[p.web_topic[r]], self.step_name[p.web_step[r]]
            base = dict(id=f"w{r}", customer_id=bid, timestamp=when(d, 13), origin="seed")
            if step in ("simulator", "tool") and topic in SIMULATION:
                out.append(em.SimulationEvent(**base, data=em.SimulationData(simulation_type=SIMULATION[topic])))
            elif step == "search" and topic in SEARCH_TEXT:
                out.append(em.KbcSearchEvent(**base, data=em.KbcSearchData(query=SEARCH_TEXT[topic])))
            elif topic in PAGE:
                out.append(em.PageViewEvent(**base, data=em.PageViewData(page=PAGE[topic])))
        if self.t.declarations is not None:
            decl = self.t.declarations[self.t.declarations["customer_id"] == p.customer_ids[i]]
            for k, row in enumerate(decl.itertuples(index=False)):
                d = day_number(row.declared_date)
                if row.event in DECLARED and a - HISTORY_DAYS <= d <= a:
                    out.append(em.DeclaredLifeEvent(id=f"d{i}-{k}", customer_id=bid, timestamp=when(d, 9),
                                                    origin="seed",
                                                    data=em.DeclaredLifeEventData(life_event=DECLARED[row.event])))
        return sorted(out, key=lambda e: e.timestamp)

    def signals(self, i: int, as_of: pd.Timestamp):
        now = datetime(as_of.year, as_of.month, as_of.day, 23, 59, tzinfo=timezone.utc)
        customer, events = self.customer(i, as_of), self.events(i, as_of)
        engines = self.ps.DEFAULT_ENGINES
        snapshot = engines.snapshot(customer, events, now)
        return customer, events, now, engines.signal.extract_all(customer, events, snapshot, now)

    def features(self, rule, signals, now) -> np.ndarray:
        """Strongest live (decayed) strength per signal type: exactly what ContextEngine sums."""
        start = now - timedelta(days=rule.ttl_days)
        best = {}
        for s in signals:
            if s.type in rule.signal_weights and self.ce._is_live(s, start, now):
                best[s.type] = max(best.get(s.type, 0.0), self.ce.ContextEngine._decayed(rule, s, now))
        return np.array([best.get(t, 0.0) for t in rule.signal_weights])


def _confidence(rule, X: np.ndarray, w: np.ndarray) -> np.ndarray:
    conf = score(X, w)
    if rule.requires_any:
        keys = list(rule.signal_weights)
        has = np.column_stack([X[:, keys.index(t)] > 0 for t in rule.requires_any if t in keys]).any(axis=1)
        conf = np.where(has, conf, np.minimum(conf, rule.cap_without_required))
    return conf


def learn(bridge: Bridge, as_ofs: list[str], sample: int | None, seed: int = 7) -> dict:
    p, mr = bridge.p, bridge.mr
    rules = {r.moment.value: r for r in mr.MOMENT_RULES}
    rng = np.random.default_rng(seed)
    who = np.flatnonzero(p.consent_tx)
    if sample and sample < len(who):
        who = np.sort(rng.choice(who, sample, replace=False))
    test_customer = rng.random(p.n) < TEST_SHARE

    X = {m: [] for m in rules}
    y = {m: [] for m in rules}
    is_test = []
    t0 = time.time()
    for as_of in as_ofs:
        ts = pd.Timestamp(as_of)
        lab = {e: labels_at(p, bridge.t.labels, EVENTS_BY_ID[e], as_of) for e in EVENT_TO_MOMENT}
        for n, i in enumerate(who):
            _, _, now, sigs = bridge.signals(i, ts)
            for m, rule in rules.items():
                X[m].append(bridge.features(rule, sigs, now))
                ev = next((e for e, mm in EVENT_TO_MOMENT.items() if mm == m), None)
                y[m].append(bool(lab[ev][i]) if ev else False)
            is_test.append(test_customer[i])
            if n and n % 500 == 0:
                print(f"  {as_of}: {n:,}/{len(who):,} customers ({time.time() - t0:.0f}s)", file=sys.stderr)
    test = np.array(is_test)

    out = {}
    for m, rule in rules.items():
        ev = next((e for e, mm in EVENT_TO_MOMENT.items() if mm == m), None)
        Xm, ym = np.vstack(X[m]), np.array(y[m])
        prior = np.array(list(rule.signal_weights.values()), dtype=float)
        entry = {"event": ev, "signals": [t.value for t in rule.signal_weights], "prior": prior.tolist(),
                 "positives": int(ym.sum()), "support": (Xm > 0).sum(axis=0).astype(int).tolist()}
        if ev and ym.sum() >= MIN_POSITIVES:
            w_train, _ = fit_weights(Xm[~test], ym[~test], prior)
            entry["test"] = {"positives": int(ym[test].sum()),
                             "hand_set": _metrics(ym[test], _confidence(rule, Xm[test], prior)),
                             "learned": _metrics(ym[test], _confidence(rule, Xm[test], w_train))}
            w, _ = fit_weights(Xm, ym, prior)
            entry["learned"] = w.tolist()
        else:
            entry["learned"] = prior.tolist()
            entry["note"] = "no ground truth for this moment" if not ev else f"fewer than {MIN_POSITIVES} cases"
        out[m] = entry
    return {"format": 1, "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "snapshots": as_ofs, "customers": int(len(who)), "threshold": "ACTIVE >= 0.40 (backend)",
            "moments": out}


def learned_rules(mr, weights: dict) -> list:
    """The backend's MOMENT_RULES with learned signal weights. TTLs and caps are unchanged."""
    rules = []
    for rule in mr.MOMENT_RULES:
        entry = weights["moments"].get(rule.moment.value)
        if entry:
            new = dict(zip(rule.signal_weights, entry["learned"]))
            rule = rule.model_copy(update={"signal_weights": new})
        rules.append(rule)
    return rules


def _fmt(x):
    return "-" if x is None else f"{x:.2f}"


def report(w: dict) -> str:
    lines = ["# KBC Context moments: hand-set vs learned weights", "",
             f"Backend pipeline run on {w['customers']:,} synthetic customers at {', '.join(w['snapshots'])}. "
             f"Scores on held-out customers ({int(TEST_SHARE * 100)}%), a moment counts when ACTIVE (>= 0.40).", "",
             "| Moment | Cases | AUC hand-set | AUC learned | Precision hand-set -> learned | Recall hand-set -> learned |",
             "|---|---:|---:|---:|---:|---:|"]
    for m, e in w["moments"].items():
        t = e.get("test")
        if not t:
            lines.append(f"| {m} | {e['positives']:,} | - | {e.get('note')} | - | - |")
            continue
        h, lr = t["hand_set"], t["learned"]
        lines.append(f"| {m} | {e['positives']:,} | {_fmt(h['auc'])} | **{_fmt(lr['auc'])}** "
                     f"| {_fmt(h['precision'])} -> {_fmt(lr['precision'])} | {_fmt(h['recall'])} -> {_fmt(lr['recall'])} |")
    lines += ["", "## Weights", ""]
    for m, e in w["moments"].items():
        lines.append(f"**{m}**" + (f" ({e['note']})" if e.get("note") else ""))
        for s, pr, lw, sup in zip(e["signals"], e["prior"], e["learned"], e["support"]):
            lines.append(f"- {s}: {pr:.2f} -> **{lw:.2f}** (seen {sup:,} times)")
        lines.append("")
    return "\n".join(lines)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("learn", "run"):
        s = sub.add_parser(name)
        s.add_argument("--backend", required=True, help="path to the backend/ folder of the KBC Context branch")
        s.add_argument("--data", required=True, help="contract folder (labels.csv needed for learn)")
    sub.choices["learn"].add_argument("--as-of", nargs="*", default=["2026-09-30", "2026-06-30", "2026-03-31"])
    sub.choices["learn"].add_argument("--sample", type=int, default=2000, help="customers per snapshot")
    sub.choices["learn"].add_argument("--out", default=str(Path(__file__).resolve().parents[2] / "artifacts"
                                                            / "kbc_context_moment_weights.json"))
    sub.choices["run"].add_argument("--customer", required=True)
    sub.choices["run"].add_argument("--as-of", default="2026-09-30")
    sub.choices["run"].add_argument("--weights", help="learned weights JSON; default: the backend's hand-set rules")
    a = ap.parse_args(argv)

    tables = contract.load(a.data, with_labels=a.cmd == "learn")
    bridge = Bridge(a.backend, tables)
    if a.cmd == "learn":
        w = learn(bridge, a.as_of, a.sample)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(w, indent=2) + "\n")
        md = Path(a.out).with_suffix(".md")
        md.write_text(report(w) + "\n")
        print(f"weights -> {a.out}\nreport -> {md}", file=sys.stderr)
        print(report(w).split("## Weights")[0])
        return

    i = int(bridge.p.position([a.customer])[0])
    if i < 0:
        raise SystemExit(f"unknown customer {a.customer}")
    ts = pd.Timestamp(a.as_of)
    customer, events, now, _ = bridge.signals(i, ts)
    engines = bridge.ps.DEFAULT_ENGINES
    if a.weights:
        rules = learned_rules(bridge.mr, json.loads(Path(a.weights).read_text()))
        engines = bridge.ps.Engines(context=bridge.ce.ContextEngine(rules=rules))
    result = bridge.ps.run_pipeline(customer, events, now, engines)
    print(json.dumps({"customer": a.customer, "events_read": len(events),
                      "moments": [m.model_dump(mode="json", include={"type", "confidence", "status"})
                                  for m in result.context.moments],
                      "intents": [x.model_dump(mode="json", include={"type", "confidence"}) for x in result.intents],
                      "decision": result.decision.model_dump(mode="json", include={"decision_type", "level", "reasons"}),
                      "experience_mode": result.experience.mode}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
