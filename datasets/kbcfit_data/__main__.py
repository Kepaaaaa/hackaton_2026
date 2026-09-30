"""Generate the KBC Fit synthetic datasets.

    python -m kbcfit_data                          # 10,000 customers into datasets/output/
    python -m kbcfit_data --customers 300 --out sample --csv
"""
import argparse
import time
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from .export import CsvWriter, SqliteWriter
from .merchants import registry
from .simulate import iso_ts, simulate_one
from .web import campaign_rows, page_rows

HERE = Path(__file__).resolve().parent.parent


def run_chunk(args):
    ids, seed = args
    parts = defaultdict(list)
    for i in ids:
        for k, v in simulate_one(i, seed).items():
            parts[k].append(v)
    out = {}
    for k, lst in parts.items():
        frames = [x for x in lst if isinstance(x, pd.DataFrame)]
        out[k] = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame([r for part in lst for r in part])
    we = out["web_events"]
    if not we.empty:
        we.insert(4, "event_ts", iso_ts(we.pop("ts").to_numpy()))
    ss = out["sessions"]
    if not ss.empty:
        ss["start_ts"] = iso_ts(ss["start_ts"].to_numpy())
        ss["end_ts"] = iso_ts(ss["end_ts"].to_numpy())
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--customers", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=str(HERE / "output"))
    ap.add_argument("--workers", type=int, default=1,
                    help="processes; 1 = plain loop (default, works in sandboxes where multiprocessing hangs)")
    ap.add_argument("--chunk", type=int, default=200)
    ap.add_argument("--csv", action="store_true", help="also write every table as CSV")
    args = ap.parse_args(argv)

    out = Path(args.out)
    t0 = time.time()
    db = SqliteWriter(out)
    csv = CsvWriter(out / "csv") if args.csv else None
    static = {"merchants": pd.DataFrame(registry().rows), "pages": pd.DataFrame(page_rows()),
              "campaigns": pd.DataFrame(campaign_rows())}
    for name, df in static.items():
        db.append(name, df)
        if csv:
            csv.append(name, df)

    ids = list(range(1, args.customers + 1))
    chunks = [(ids[i:i + args.chunk], args.seed) for i in range(0, len(ids), args.chunk)]
    counts = defaultdict(int)
    done = 0
    pool = Pool(args.workers) if args.workers > 1 else None
    parts = pool.imap(run_chunk, chunks) if pool else map(run_chunk, chunks)
    for part in parts:
        for name, df in part.items():
            db.append(name, df)
            if csv:
                csv.append(name, df)
            counts[name] += len(df)
        done += len(part["customers"])
        print(f"\r{done:>7,}/{args.customers:,} customers  {counts['transactions']:>11,} transactions  "
              f"{counts['web_events']:>11,} web events  {time.time() - t0:6.0f}s", end="", flush=True)
    if pool:
        pool.close()
    db.close()
    print(f"\nwritten to {out}/ in {time.time() - t0:.0f}s")
    for name, n in sorted(counts.items()):
        print(f"  {name:<22}{n:>12,}")
    from .checks import report
    report(out)


if __name__ == "__main__":
    main()
