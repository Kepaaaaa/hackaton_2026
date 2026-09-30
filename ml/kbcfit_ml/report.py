"""Compose the per-customer JSON: `transactions` (life events) and `searches` (website interest).

Signals follow the frozen `Signal` shape of src/lib/engine/types.ts: id, label, detail, source,
weight. `confidence` is exactly the sum of the listed weights (capped at 1), so switching a
signal off in the app gives the same number the model would.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .catalog import (EVENTS, SEARCH_HALF_LIFE_DAYS, SEARCH_LOOKBACK_DAYS, SEARCH_MIN_SCORE, SEARCH_SCALE,
                      SIGNALS, STEP_WEIGHT, TOPICS)
from .contract import STEPS
from .model import THRESHOLD, weights_of
from .signals import Prepared, SignalValues, day_number, evaluate, event_matrix, from_day_number, signal_key

EVIDENCE_LIMIT = 5


def _date(day: int) -> str:
    ts = pd.Timestamp(from_day_number(day))
    return f"{ts.day} {ts:%b %Y}"


def _eur(x: float) -> str:
    return f"€{x:,.0f}"


def _evidence(p: Prepared, v: SignalValues, wanted: np.ndarray) -> dict[int, dict]:
    """Latest evidence rows per customer, only for customers where the signal fired."""
    if v.rows is None or not len(v.rows):
        return {}
    if v.table == "tx":
        c, day, ref, name = p.tx_c[v.rows], p.tx_day[v.rows], p.tx_id[v.rows], p.tx_counterparty[v.rows]
    elif v.table == "web":
        c, day, ref, name = p.web_c[v.rows], p.web_day[v.rows], p.web_page[v.rows], p.web_page[v.rows]
    else:
        return {}
    keep = v.fired[c] & wanted[c]
    df = pd.DataFrame({"c": c[keep], "day": day[keep], "ref": ref[keep], "name": name[keep]})
    if v.table == "web":
        df = df.drop_duplicates(["c", "ref"], keep="last")
    df = df.sort_values(["c", "day"], ascending=[True, False]).groupby("c").head(EVIDENCE_LIMIT)
    out = {}
    for cid, g in df.groupby("c", sort=False):
        names = [n for n in dict.fromkeys(g["name"]) if n][:2]
        out[int(cid)] = {"refs": g["ref"].tolist(), "names": names}
    return out


def _detail(sid: str, v: SignalValues, i: int, names: list[str]) -> str:
    r = SIGNALS[sid].rule
    n, total, first, last = int(v.count[i]), float(v.total[i]), int(v.first[i]), int(v.last[i])
    who = f" ({', '.join(names)})" if names else ""
    if r.kind == "declared":
        return f"You told us on {_date(last)}"
    if r.kind == "web":
        return f"{n} visit{'s' * (n > 1)}, last on {_date(last)}"
    if r.kind == "stopped":
        return f"Last one on {_date(last)}, none since{who}"
    if r.kind == "new_payer":
        return f"First payment on {_date(first)}{who}"
    if r.kind == "onset":
        return f"Since {_date(first)}: {n} payment{'s' * (n > 1)}, {_eur(total)}{who}"
    if r.kind == "spike":
        ratio = v.ratio[i]
        usual = "none before" if not np.isfinite(ratio) else f"{ratio:.1f}x the usual"
        return f"{_eur(total)} in the last {r.window // 30} months, {usual}"
    if n == 1:
        return f"{_eur(total)} {'received ' * (r.direction == 'in')}on {_date(last)}{who}"
    noun = "payments received" if r.direction == "in" else "payments"
    return f"{n} {noun}, {_eur(total)} in total, last on {_date(last)}{who}"


def _status(event, confidence: float, active: set[str]) -> str:
    if confidence < THRESHOLD:
        return "below_threshold"
    if event.sensitive and "declared" not in active:
        return "ask_customer"      # never proposed on inference alone: the customer confirms first
    return "ready"


def search_interest(p: Prepared, as_of) -> dict[int, list[dict]]:
    a = day_number(as_of)
    age = a - p.web_day
    topic_names = np.array(list(p.topic_code), dtype=object)
    step_names = np.array(list(p.step_code), dtype=object)
    m = (age >= 0) & (age < SEARCH_LOOKBACK_DAYS)
    if not m.any():
        return {}
    df = pd.DataFrame({"c": p.web_c[m], "topic": topic_names[p.web_topic[m]], "step": step_names[p.web_step[m]],
                       "day": p.web_day[m], "age": age[m], "page": p.web_page[m], "session": p.web_session[m]})
    df = df[df["topic"].isin(TOPICS)]
    if df.empty:
        return {}
    df["points"] = df["step"].map(STEP_WEIGHT) * 0.5 ** (df["age"] / SEARCH_HALF_LIFE_DAYS)
    df["rank"] = df["step"].map({s: i for i, s in enumerate(STEPS)})
    df["visit"] = np.where(df["session"] != "", df["session"], df["day"].astype(str))
    g = df.groupby(["c", "topic"])
    agg = g.agg(points=("points", "sum"), events=("points", "size"), sessions=("visit", "nunique"),
                last=("day", "max"), rank=("rank", "max")).reset_index()
    agg["score"] = 1 - np.exp(-agg["points"] / SEARCH_SCALE)
    agg = agg[agg["score"] >= SEARCH_MIN_SCORE]
    pages = (df.groupby(["c", "topic"])["page"].agg(lambda s: s.value_counts().index[:3].tolist()))
    out = defaultdict(list)
    for r in agg.sort_values(["c", "score"], ascending=[True, False]).itertuples(index=False):
        label, products, sensitive = TOPICS[r.topic]
        out[int(r.c)].append({
            "topic": r.topic, "label": label, "score": round(float(r.score), 2),
            "events": int(r.events), "sessions": int(r.sessions), "last_visit": from_day_number(int(r.last)),
            "deepest_step": STEPS[int(r.rank)], "top_pages": pages[(r.c, r.topic)],
            "products": list(products), "sensitive": sensitive,
        })
    return out


def compose(p: Prepared, model: dict, as_of, only: list[str] | None = None):
    """Yield one JSON-ready dict per customer (all customers, or the ids in `only`)."""
    wanted = np.zeros(p.n, bool)
    if only:
        pos = p.position(only)
        if (pos < 0).any():
            missing = [c for c, i in zip(only, pos) if i < 0]
            raise KeyError(f"unknown customer ids {missing[:5]}")
        wanted[pos] = True
    else:
        wanted[:] = True

    values = evaluate(p, as_of, keep_rows=True)
    evidence = {k: _evidence(p, v, wanted) for k, v in values.items()}
    per_event = []
    for e in EVENTS:
        ids, X = event_matrix(values, e)
        w = weights_of(model, e.id)
        per_event.append((e, ids, X, w, np.clip(X @ w, 0, 1)))
    searches = search_interest(p, as_of)
    meta = {"version": model["version"], "source": model["source"], "threshold": THRESHOLD}

    for i in np.flatnonzero(wanted):
        events = []
        for e, ids, X, w, conf in per_event:
            if conf[i] <= 0:
                continue
            signals, active = [], set()
            for j, sid in enumerate(ids):
                if not X[i, j] or w[j] <= 0:
                    continue
                key = signal_key(e.id, sid)
                ev = evidence[key].get(int(i), {"refs": [], "names": []})
                active.add(sid)
                signals.append({"id": sid, "label": SIGNALS[sid].label,
                                "detail": _detail(sid, values[key], i, ev["names"]),
                                "source": SIGNALS[sid].source, "weight": float(w[j]), "evidence": ev["refs"]})
            confidence = round(min(1.0, sum(s["weight"] for s in signals)), 2)
            events.append({"event": e.id, "label": e.label, "confidence": confidence,
                           "status": _status(e, confidence, active), "sensitive": e.sensitive,
                           "products": list(e.products), "signals": signals})
        events.sort(key=lambda x: -x["confidence"])
        yield {
            "customer_id": str(p.customer_ids[i]),
            "as_of": str(pd.Timestamp(as_of).date()),
            "model": meta,
            "consent": {"transactions": bool(p.consent_tx[i]), "search": bool(p.consent_web[i])},
            "transactions": events,
            "searches": searches.get(int(i), []),
        }
