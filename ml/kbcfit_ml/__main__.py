"""Command line: train on any folder that follows the data contract, then predict.

    python -m kbcfit_ml train   --data data/synthetic
    python -m kbcfit_ml predict --data data/synthetic --customer C0000001
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from . import contract, model
from .catalog import EVENTS_BY_ID, SIGNALS
from .report import compose
from .signals import from_day_number, prepare

DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "artifacts" / "model.json"


def _fmt(x) -> str:
    return "-" if x is None else f"{x:.2f}"


def model_card(m: dict) -> str:
    lines = [
        "# KBC Fit signal model: model card",
        "",
        f"- Version: `{m['version']}`",
        f"- Trained on: **{m['source']}**, {m['customers']:,} customers, snapshots {', '.join(m['snapshots'])}",
        f"- A card is shown when confidence >= {m['threshold']} (confidence = sum of the active signal weights)",
        f"- Scores below are measured on customers held out of training ({int(model.TEST_SHARE * 100)}%)",
        "",
        "| Event | Labelled cases | AUC expert priors | AUC learned | AUC black box | Precision @0.6 | Recall @0.6 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for eid, e in m["events"].items():
        t = e.get("test")
        if not t:
            lines.append(f"| {e['label']}{' (sensitive)' * e['sensitive']} | {e.get('positives', 0):,} "
                         f"| - | not trained | - | - | - |")
            continue
        lr, ex = t["learned"], t["expert_priors"]
        lines.append(f"| {e['label']}{' (sensitive)' * e['sensitive']} | {e['positives']:,} | {_fmt(ex['auc'])} "
                     f"| **{_fmt(lr['auc'])}** | {_fmt(lr['black_box_auc'])} | {_fmt(lr['precision'])} "
                     f"| {_fmt(lr['recall'])} |")
    lines += ["", "## Weights (expert prior -> learned)", ""]
    for eid, e in m["events"].items():
        lines.append(f"**{e['label']}**{' (not trained: ' + e['note'] + ')' if e.get('note') else ''}")
        lines.append("")
        for sid, w in e["weights"].items():
            sup = e.get("support", {}).get(sid)
            lines.append(f"- {SIGNALS[sid].label}: {e['priors'][sid]:.2f} -> **{w:.2f}**"
                         + (f" (seen {sup:,} times{', too rare to learn: prior kept' if sup < m['min_support'] and e['trained'] else ''})" if sup is not None else ""))
        lines.append("")
    return "\n".join(lines)


def cmd_train(a) -> None:
    t0 = time.time()
    tables = contract.load(a.data, with_labels=True)
    p = prepare(tables)
    as_ofs = a.as_of or model.snapshot_dates(p, a.every, a.snapshots)
    print(f"{p.n:,} customers, {len(p.tx_day):,} transactions, {len(p.web_day):,} web events; "
          f"snapshots {', '.join(as_ofs)}", file=sys.stderr)
    m = model.train(p, tables.labels, as_ofs, a.source or Path(a.data).name)
    model.save(m, a.out)
    card = Path(a.out).with_name("model_card.md")
    card.write_text(model_card(m) + "\n")
    print(f"model -> {a.out}\nmodel card -> {card}  ({time.time() - t0:.0f}s)", file=sys.stderr)
    for eid, e in m["events"].items():
        lr = e.get("test", {}).get("learned")
        ex = e.get("test", {}).get("expert_priors")
        line = f"  {eid:28s} cases {e.get('positives', 0):6,d}  "
        line += (f"AUC expert {_fmt(ex['auc'])} -> learned {_fmt(lr['auc'])} (black box {_fmt(lr['black_box_auc'])})"
                 f"  precision {_fmt(lr['precision'])} recall {_fmt(lr['recall'])}") if lr else "expert priors kept"
        print(line, file=sys.stderr)


def cmd_predict(a) -> None:
    m = model.untrained() if a.expert_priors else model.load(a.model)
    tables = contract.load(a.data)
    p = prepare(tables)
    as_of = a.as_of or from_day_number(int(max(p.tx_day.max(initial=0), p.web_day.max(initial=0))))
    rows = compose(p, m, as_of, only=a.customer)
    if a.customer and not a.out:
        docs = list(rows)
        print(json.dumps(docs[0] if len(docs) == 1 else docs, indent=2, ensure_ascii=False))
        return
    out = open(a.out, "w") if a.out else sys.stdout
    n = 0
    for doc in rows:
        out.write(json.dumps(doc, ensure_ascii=False) + "\n")
        n += 1
    if a.out:
        out.close()
        print(f"{n:,} customers -> {a.out}", file=sys.stderr)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="kbcfit_ml", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("train", help="learn the signal weights from labelled outcomes")
    t.add_argument("--data", required=True, help="folder with the contract CSV files, labels.csv included")
    t.add_argument("--out", default=str(DEFAULT_MODEL))
    t.add_argument("--source", help="name of the data source, stored in the model card")
    t.add_argument("--as-of", nargs="*", help="snapshot dates; default: every --every days back from the end")
    t.add_argument("--every", type=int, default=91)
    t.add_argument("--snapshots", type=int, default=6)
    t.set_defaults(func=cmd_train)

    pr = sub.add_parser("predict", help="write the JSON for each customer")
    pr.add_argument("--data", required=True)
    pr.add_argument("--model", default=str(DEFAULT_MODEL))
    pr.add_argument("--expert-priors", action="store_true", help="ignore the trained model, use the expert priors")
    pr.add_argument("--as-of", help="default: last date in the data")
    pr.add_argument("--customer", nargs="*", help="only these customer ids (pretty-printed when no --out)")
    pr.add_argument("--out", help="JSON Lines file; default: stdout")
    pr.set_defaults(func=cmd_predict)

    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
