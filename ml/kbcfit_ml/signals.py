"""Evaluate every signal for every customer at one as-of date, point in time.

Only rows dated on or before the as-of date are read, so a model trained on past snapshots
never sees the future. Each rule is one vectorised pass over all customers.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .catalog import EVENTS, SIGNALS, Rule
from .contract import Tables

FAR_PAST = np.iinfo(np.int32).min // 2
FAR_FUTURE = np.iinfo(np.int32).max // 2


def day_number(d) -> int:
    return int(np.datetime64(pd.Timestamp(d).date(), "D").astype(np.int64))


def from_day_number(n: int) -> str:
    return str(np.datetime64(int(n), "D"))


def _days(values) -> np.ndarray:
    return np.asarray(values, dtype="datetime64[D]").astype(np.int64).astype(np.int32)


@dataclass
class Prepared:
    """The contract tables as flat numpy arrays, customers addressed by position."""
    customer_ids: np.ndarray
    consent_tx: np.ndarray
    consent_web: np.ndarray
    tx_c: np.ndarray
    tx_day: np.ndarray
    tx_amt: np.ndarray
    tx_cat: np.ndarray
    tx_cp: np.ndarray
    tx_abroad: np.ndarray
    tx_id: np.ndarray
    tx_counterparty: np.ndarray
    cat_code: dict
    first_day: np.ndarray
    web_c: np.ndarray
    web_day: np.ndarray
    web_topic: np.ndarray
    web_step: np.ndarray
    web_page: np.ndarray
    web_session: np.ndarray
    topic_code: dict
    step_code: dict
    decl_c: np.ndarray
    decl_day: np.ndarray
    decl_event: np.ndarray

    @property
    def n(self) -> int:
        return len(self.customer_ids)

    def position(self, customer_ids) -> np.ndarray:
        return pd.Index(self.customer_ids).get_indexer(pd.Series(customer_ids).astype(str))


def prepare(t: Tables) -> Prepared:
    ids = t.customers["customer_id"].to_numpy(dtype=object)
    index = pd.Index(ids)

    tx = t.transactions
    tx_c = index.get_indexer(tx["customer_id"])
    tx = tx[tx_c >= 0]
    tx_c = tx_c[tx_c >= 0]
    order = np.lexsort((_days(tx["booking_date"].values), tx_c))
    tx, tx_c = tx.iloc[order], tx_c[order]
    cat, cats = pd.factorize(tx["category"])
    if "counterparty" in tx:
        cp, _ = pd.factorize(tx["counterparty"])
        counterparty = tx["counterparty"].fillna("").to_numpy(dtype=object)
    else:
        cp = np.full(len(tx), -1)
        counterparty = np.full(len(tx), "", dtype=object)
    abroad = (tx["country"].notna() & (tx["country"] != "BE")).to_numpy() if "country" in tx \
        else np.zeros(len(tx), bool)
    tx_day = _days(tx["booking_date"].values)
    first_day = np.full(len(ids), FAR_FUTURE, dtype=np.int64)
    np.minimum.at(first_day, tx_c, tx_day)

    web = t.web_events
    web_c = index.get_indexer(web["customer_id"])
    web = web[web_c >= 0]
    web_c = web_c[web_c >= 0]
    topic, topics = pd.factorize(web["topic"])
    step, steps = pd.factorize(web["step"])
    page = web["page"].fillna("").to_numpy(dtype=object) if "page" in web else web["topic"].to_numpy(dtype=object)
    session = web["session_id"].astype(str).to_numpy(dtype=object) if "session_id" in web \
        else np.full(len(web), "", dtype=object)

    decl = t.declarations if t.declarations is not None else \
        pd.DataFrame({"customer_id": [], "event": [], "declared_date": pd.to_datetime([])})
    decl_c = index.get_indexer(decl["customer_id"])
    decl = decl[decl_c >= 0]

    return Prepared(
        customer_ids=ids,
        consent_tx=t.customers["consent_transactions"].to_numpy(bool),
        consent_web=t.customers["consent_search"].to_numpy(bool),
        tx_c=tx_c.astype(np.int64), tx_day=tx_day, tx_amt=tx["amount"].to_numpy(float), tx_cat=cat,
        tx_cp=cp, tx_abroad=abroad, tx_id=tx["transaction_id"].to_numpy(dtype=object), tx_counterparty=counterparty,
        cat_code={c: i for i, c in enumerate(cats)}, first_day=first_day,
        web_c=web_c.astype(np.int64), web_day=_days(web["timestamp"].values), web_topic=topic, web_step=step,
        web_page=page, web_session=session,
        topic_code={c: i for i, c in enumerate(topics)}, step_code={c: i for i, c in enumerate(steps)},
        decl_c=decl_c[decl_c >= 0].astype(np.int64), decl_day=_days(decl["declared_date"].values),
        decl_event=decl["event"].to_numpy(dtype=object),
    )


@dataclass
class SignalValues:
    """One signal for all customers. `rows` indexes the evidence rows (tx, web or decl table)."""
    fired: np.ndarray
    count: np.ndarray
    total: np.ndarray
    first: np.ndarray
    last: np.ndarray
    table: str
    rows: np.ndarray | None = None
    ratio: np.ndarray | None = None


def _lut(codes: dict, names) -> np.ndarray:
    lut = np.zeros(max(len(codes), 1), bool)
    for name in names:
        if name in codes:
            lut[codes[name]] = True
    return lut


def _aggregate(n, c, day, amt, m, table, keep_rows) -> SignalValues:
    cc = c[m]
    cnt = np.bincount(cc, minlength=n)
    tot = np.bincount(cc, weights=np.abs(amt[m]), minlength=n) if amt is not None else np.zeros(n)
    first = np.full(n, FAR_FUTURE, dtype=np.int64)
    last = np.full(n, FAR_PAST, dtype=np.int64)
    np.minimum.at(first, cc, day[m])
    np.maximum.at(last, cc, day[m])
    rows = np.flatnonzero(m) if keep_rows else None
    return SignalValues(cnt > 0, cnt, tot, first, last, table, rows)


def _tx_rule(p: Prepared, r: Rule, db: np.ndarray, a: int, keep_rows: bool) -> SignalValues:
    n, W, B = p.n, r.window, r.baseline
    if r.kind == "abroad":
        base = p.tx_abroad & (p.tx_amt < 0)
    else:
        base = _lut(p.cat_code, r.categories)[p.tx_cat] if len(p.tx_cat) else np.zeros(0, bool)
        if r.direction == "out":
            base &= p.tx_amt < 0
        elif r.direction == "in":
            base &= p.tx_amt > 0
        if r.min_amount:
            base &= np.abs(p.tx_amt) >= r.min_amount
    recent = base & (db >= 0) & (db < W)
    before = base & (db >= W) & (db < W + B)
    history = (a - p.first_day) >= W + B // 2
    agg = lambda m: _aggregate(n, p.tx_c, p.tx_day, p.tx_amt, m, "tx", keep_rows)  # noqa: E731

    if r.kind in ("count", "abroad"):
        v = agg(recent)
        v.fired = (v.count >= r.min_count) & (v.total >= r.min_total)
    elif r.kind == "onset":
        v = agg(recent)
        had_before = np.bincount(p.tx_c[before], minlength=n) > 0
        v.fired = (v.count >= r.min_count) & ~had_before & history
    elif r.kind == "stopped":
        v = agg(before)
        still_now = np.bincount(p.tx_c[recent], minlength=n) > 0
        active = np.bincount(p.tx_c[(db >= 0) & (db < W)], minlength=n) > 0
        v.fired = (v.count >= r.min_count) & ~still_now & active
    elif r.kind == "spike":
        v = agg(recent)
        base_total = np.bincount(p.tx_c[before], weights=np.abs(p.tx_amt[before]), minlength=n)
        rate_now, rate_before = v.total / W, base_total / B
        with np.errstate(divide="ignore", invalid="ignore"):
            v.ratio = np.where(rate_before > 0, rate_now / rate_before, np.inf)
        v.fired = (v.total >= r.min_total) & (rate_now >= r.factor * rate_before) & history
    elif r.kind == "new_payer":
        width = int(p.tx_cp.max(initial=0)) + 2
        key = p.tx_c * width + (p.tx_cp + 1)
        seen = np.unique(key[before])
        new_rows = recent & (p.tx_cp >= 0) & ~np.isin(key, seen)
        v = agg(new_rows)
        had_before = np.bincount(p.tx_c[before], minlength=n) > 0
        v.fired = (v.count >= 1) & had_before
    else:
        raise ValueError(f"unknown rule kind {r.kind}")
    return v


def _web_rule(p: Prepared, r: Rule, wdb: np.ndarray, keep_rows: bool) -> SignalValues:
    m = _lut(p.topic_code, r.topics)[p.web_topic] if len(p.web_topic) else np.zeros(0, bool)
    if r.steps:
        m &= _lut(p.step_code, r.steps)[p.web_step]
    m &= (wdb >= 0) & (wdb < r.window)
    v = _aggregate(p.n, p.web_c, p.web_day, None, m, "web", keep_rows)
    v.fired = v.count >= r.min_count
    return v


def _declared(p: Prepared, event: str, a: int, window: int, keep_rows: bool) -> SignalValues:
    ddb = a - p.decl_day
    m = (p.decl_event == event) & (ddb >= 0) & (ddb < window)
    return _aggregate(p.n, p.decl_c, p.decl_day, None, m, "decl", keep_rows)


def signal_key(event_id: str, signal_id: str) -> str:
    """`declared` depends on the event (declared WHAT?), every other signal is shared."""
    return f"declared:{event_id}" if signal_id == "declared" else signal_id


def evaluate(p: Prepared, as_of, keep_rows: bool = False) -> dict[str, SignalValues]:
    a = day_number(as_of)
    db = a - p.tx_day
    wdb = a - p.web_day
    out = {}
    for sid, s in SIGNALS.items():
        if s.rule.kind == "declared":
            continue
        out[sid] = _web_rule(p, s.rule, wdb, keep_rows) if s.rule.kind == "web" else \
            _tx_rule(p, s.rule, db, a, keep_rows)
    for e in EVENTS:
        if "declared" in e.priors:
            out[signal_key(e.id, "declared")] = _declared(p, e.id, a, e.declaration_days, keep_rows)
    return out


def event_matrix(values: dict[str, SignalValues], event) -> tuple[list[str], np.ndarray]:
    """Fired signals of one event as a 0/1 matrix (customers x signals), in catalog order."""
    ids = list(event.priors)
    X = np.column_stack([values[signal_key(event.id, s)].fired for s in ids]).astype(np.float64)
    return ids, X


def labels_at(p: Prepared, labels: pd.DataFrame, event, as_of) -> np.ndarray:
    """1 where the customer is in this life event at the as-of date, according to the labels."""
    y = np.zeros(p.n, bool)
    rows = labels[labels["event"] == event.id]
    if rows.empty:
        return y
    if "event_date" in rows and rows["event_date"].notna().any():
        before, after = event.label_window
        delta = (rows["event_date"] - pd.Timestamp(as_of)).dt.days
        rows = rows[(delta >= -before) & (delta <= after)]
    pos = p.position(rows["customer_id"])
    y[pos[pos >= 0]] = True
    return y
