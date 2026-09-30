"""Learn one weight per (event, signal) from the bank's own outcomes.

The model is deliberately additive: confidence = sum of the weights of the active signals,
capped at 1. That is the rule of the engine (src/lib/engine/types.ts), so the app can switch a
signal off and recompute the confidence without calling the model again.

Weights are fitted by least squares with a positivity constraint and no intercept: a customer
with no active signal has confidence 0, and a signal can only add evidence, never remove it.
A gradient-boosting model is trained on the same signals only to measure what this
explainability costs.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import Ridge
from sklearn.metrics import brier_score_loss, roc_auc_score

from .catalog import EVENTS, EVENTS_BY_ID, SIGNALS
from .signals import Prepared, evaluate, event_matrix, from_day_number, labels_at

THRESHOLD = 0.6          # frozen in src/lib/engine/types.ts
MIN_POSITIVES = 30       # fewer labelled cases than this: keep the expert priors
MIN_SUPPORT = 20         # a signal seen fewer times than this keeps its expert prior
TEST_SHARE = 0.2
FORMAT = 1


@dataclass
class Dataset:
    """Stacked snapshots: one row per (as-of date, customer)."""
    as_ofs: list[str]
    customer_pos: np.ndarray
    X: dict[str, np.ndarray]
    y: dict[str, np.ndarray]


def snapshot_dates(p: Prepared, every_days: int = 91, max_snapshots: int = 6) -> list[str]:
    """As-of dates from the end of the data backwards, as long as every rule has enough history."""
    if not len(p.tx_day):
        raise ValueError("no transactions to train on")
    span = max(s.rule.window + s.rule.baseline for s in SIGNALS.values())
    last, earliest = int(p.tx_day.max()), int(p.tx_day.min()) + span
    dates = [last - k * every_days for k in range(max_snapshots) if last - k * every_days >= earliest]
    return [from_day_number(d) for d in (dates or [last])]


def build_dataset(p: Prepared, labels, as_ofs: list[str]) -> Dataset:
    X = {e.id: [] for e in EVENTS}
    y = {e.id: [] for e in EVENTS}
    for as_of in as_ofs:
        values = evaluate(p, as_of)
        for e in EVENTS:
            X[e.id].append(event_matrix(values, e)[1])
            y[e.id].append(labels_at(p, labels, e, as_of))
    pos = np.tile(np.arange(p.n), len(as_ofs))
    return Dataset(as_ofs, pos, {k: np.vstack(v) for k, v in X.items()}, {k: np.concatenate(v) for k, v in y.items()})


def fit_weights(X: np.ndarray, y: np.ndarray, prior: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Learn the weights of well-observed signals. A signal seen fewer than MIN_SUPPORT times keeps
    its expert prior, and the others are fitted on what it leaves unexplained."""
    support = X.sum(axis=0).astype(int)
    usable = support >= MIN_SUPPORT
    w = np.where(usable, 0.0, prior)
    if usable.any() and y.sum() >= MIN_POSITIVES:
        residual = y.astype(float) - X[:, ~usable] @ w[~usable]
        reg = Ridge(alpha=1.0, positive=True, fit_intercept=False).fit(X[:, usable], residual)
        w[usable] = reg.coef_
    return np.clip(np.round(w, 2), 0.0, 1.0), support


def score(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    return np.clip(X @ w, 0.0, 1.0)


def _metrics(y: np.ndarray, s: np.ndarray) -> dict:
    shown = s >= THRESHOLD
    both = 0 < y.sum() < len(y)
    return {
        "auc": round(float(roc_auc_score(y, s)), 3) if both else None,
        "precision": round(float(y[shown].mean()), 3) if shown.any() else None,
        "recall": round(float(shown[y].mean()), 3) if y.any() else None,
        "shown": int(shown.sum()),
        "brier": round(float(brier_score_loss(y, s)), 4) if both else None,
    }


def _black_box_auc(Xtr, ytr, Xte, yte) -> float | None:
    if ytr.sum() < MIN_POSITIVES or not 0 < yte.sum() < len(yte):
        return None
    gb = HistGradientBoostingClassifier(max_iter=200, random_state=0).fit(Xtr, ytr)
    return round(float(roc_auc_score(yte, gb.predict_proba(Xte)[:, 1])), 3)


def train(p: Prepared, labels, as_ofs: list[str], source: str, seed: int = 7) -> dict:
    ds = build_dataset(p, labels, as_ofs)
    rng = np.random.default_rng(seed)
    test_customers = rng.random(p.n) < TEST_SHARE
    test = test_customers[ds.customer_pos]      # same customer never on both sides

    events = {}
    for e in EVENTS:
        ids, X, y = list(e.priors), ds.X[e.id], ds.y[e.id]
        prior = np.array([e.priors[s] for s in ids])
        entry = {"label": e.label, "sensitive": e.sensitive, "positives": int(y.sum()), "rows": int(len(y))}
        if y.sum() >= MIN_POSITIVES:
            w_train, _ = fit_weights(X[~test], y[~test], prior)
            learned = _metrics(y[test], score(X[test], w_train))
            learned["black_box_auc"] = _black_box_auc(X[~test], y[~test], X[test], y[test])
            entry["test"] = {"positives": int(y[test].sum()), "rows": int(test.sum()),
                             "learned": learned, "expert_priors": _metrics(y[test], score(X[test], prior))}
            w, support = fit_weights(X, y, prior)      # final weights use every customer
            entry["trained"] = True
        else:
            w, support = prior, X.sum(axis=0).astype(int)
            entry["trained"] = False
            entry["note"] = f"fewer than {MIN_POSITIVES} labelled cases: expert priors kept"
        entry["weights"] = {s: float(v) for s, v in zip(ids, w)}
        entry["priors"] = {s: float(v) for s, v in zip(ids, prior)}
        entry["support"] = {s: int(v) for s, v in zip(ids, support)}
        events[e.id] = entry

    return {
        "format": FORMAT,
        "version": datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + f"-{source}",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "customers": int(p.n),
        "snapshots": as_ofs,
        "threshold": THRESHOLD,
        "min_support": MIN_SUPPORT,
        "events": events,
    }


def untrained() -> dict:
    """Expert priors only: what runs on day one at a bank, before any outcome is known."""
    return {"format": FORMAT, "version": "expert-priors", "trained_at": None, "source": "expert priors",
            "customers": 0, "snapshots": [], "threshold": THRESHOLD, "min_support": MIN_SUPPORT,
            "events": {e.id: {"label": e.label, "sensitive": e.sensitive, "trained": False,
                              "weights": dict(e.priors), "priors": dict(e.priors)} for e in EVENTS}}


def weights_of(model: dict, event_id: str) -> np.ndarray:
    e = EVENTS_BY_ID[event_id]
    stored = model["events"].get(event_id, {}).get("weights", e.priors)
    return np.array([stored.get(s, 0.0) for s in e.priors])


def save(model: dict, path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(model, indent=2, ensure_ascii=False) + "\n")


def load(path: str | Path) -> dict:
    model = json.loads(Path(path).read_text())
    if model.get("format") != FORMAT:
        raise ValueError(f"{path}: unsupported model format {model.get('format')}")
    return model
