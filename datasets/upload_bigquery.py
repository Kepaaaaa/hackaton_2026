"""Load the generated SQLite databases into Google Cloud BigQuery.

    pip install google-cloud-bigquery
    export GCP_PROJECT_ID=... GCP_CLIENT_EMAIL=... GCP_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\\n..."
    python upload_bigquery.py                       # loads output/*.sqlite into kbcfit_bank, kbcfit_web, kbcfit_labels
    python upload_bigquery.py --dry-run             # shows tables, row counts and schemas, sends nothing

Credentials come from the same environment variables as the app (never from a file in Git). If they are
not set, the Google client falls back to Application Default Credentials (`gcloud auth application-default login`).
The labels go to their own dataset so that access to the ground truth can be restricted separately.
"""
import argparse
import gzip
import os
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATASETS = {"bank": "kbcfit_bank", "web": "kbcfit_web", "labels": "kbcfit_labels"}


BOOL_PREFIXES = ("is_", "has_", "consent_", "declared_by", "trait_")


def bq_type(column: str, sqlite_type: str) -> str:
    if column.endswith("_date") or column == "customer_since":
        return "DATE"
    if column.endswith("_ts"):
        return "DATETIME"
    t = (sqlite_type or "").upper()
    if column in ("postcode", "last4"):
        return "STRING"
    if "INT" in t:
        # pandas stores booleans as 0/1 integers; numeric traits are REAL, so INTEGER trait_* are flags
        return "BOOL" if column.startswith(BOOL_PREFIXES) else "INT64"
    if "REAL" in t or "FLOA" in t or "DOUB" in t:
        return "FLOAT64"
    return "STRING"


def client_from_env():
    from google.cloud import bigquery
    from google.oauth2 import service_account

    project = os.environ.get("GCP_PROJECT_ID")
    email, key = os.environ.get("GCP_CLIENT_EMAIL"), os.environ.get("GCP_PRIVATE_KEY")
    if email and key:
        info = {"type": "service_account", "project_id": project, "client_email": email,
                "private_key": key.replace("\\n", "\n"), "token_uri": "https://oauth2.googleapis.com/token"}
        creds = service_account.Credentials.from_service_account_info(info)
        return bigquery.Client(project=project, credentials=creds)
    return bigquery.Client(project=project)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(HERE / "output"))
    ap.add_argument("--location", default="EU", help="BigQuery location; EU keeps the data in Europe")
    ap.add_argument("--prefix", default="", help="optional prefix for dataset names, e.g. 'dev_'")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    client = None if args.dry_run else client_from_env()
    if client:
        from google.cloud import bigquery
    for db, dataset in DATASETS.items():
        path = Path(args.src) / f"{db}.sqlite"
        con = sqlite3.connect(path)
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        ds_id = f"{args.prefix}{dataset}"
        if client:
            ds = bigquery.Dataset(f"{client.project}.{ds_id}")
            ds.location = args.location
            client.create_dataset(ds, exists_ok=True)
        for table in tables:
            cols = con.execute(f"PRAGMA table_info({table})").fetchall()
            schema = [(c[1], bq_type(c[1], c[2])) for c in cols]
            n = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{ds_id}.{table:<22} {n:>12,} rows   " + ", ".join(f"{c}:{t}" for c, t in schema[:6]) + " ...")
            if not client:
                continue
            table_id = f"{client.project}.{ds_id}.{table}"
            job_config = bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.CSV, skip_leading_rows=1, allow_quoted_newlines=True,
                schema=[bigquery.SchemaField(c, t) for c, t in schema],
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
            first = True
            for chunk in pd.read_sql_query(f"SELECT * FROM {table}", con, chunksize=1_000_000):
                for c, t in schema:
                    if t == "BOOL":
                        chunk[c] = chunk[c].map({1: "true", 0: "false", True: "true", False: "false"})
                with tempfile.NamedTemporaryFile(suffix=".csv.gz", delete=False) as tmp:
                    with gzip.open(tmp.name, "wt", newline="") as f:
                        chunk.to_csv(f, index=False)
                    with open(tmp.name, "rb") as f:
                        client.load_table_from_file(f, table_id, job_config=job_config).result()
                os.unlink(tmp.name)
                if first:
                    job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND
                    first = False
        con.close()
    print("done" if client else "dry run: nothing sent")


if __name__ == "__main__":
    main()
