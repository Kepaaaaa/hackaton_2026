"""Writers: SQLite databases and CSV. Mapping onto the ML data contract lives in ml/kbcfit_ml/adapters/."""
import sqlite3
from pathlib import Path

import pandas as pd

DATABASES = {
    # observable by the bank
    "bank": ["customers", "accounts", "transactions", "insurance_contracts", "declared_situations",
             "monthly_balances", "merchants"],
    "web": ["pages", "campaigns", "sessions", "web_events"],
    # ground truth: never read by a detector, only used to score it
    "labels": ["life_events", "transaction_signals", "web_signals", "customer_truth", "external_products"],
}
INDEXES = {
    "transactions": ["customer_id", "account_id", "booking_date", "category"],
    "accounts": ["customer_id"], "monthly_balances": ["customer_id"], "insurance_contracts": ["customer_id"],
    "sessions": ["customer_id"], "web_events": ["customer_id", "session_id", "topic"],
    "life_events": ["customer_id", "event_type"], "transaction_signals": ["event_id", "transaction_id"],
    "web_signals": ["event_id"],
}

class SqliteWriter:
    def __init__(self, out_dir: Path):
        out_dir.mkdir(parents=True, exist_ok=True)
        self.conns = {}
        for db in DATABASES:
            path = out_dir / f"{db}.sqlite"
            if path.exists():
                path.unlink()
            con = sqlite3.connect(path)
            con.execute("PRAGMA journal_mode=OFF")
            con.execute("PRAGMA synchronous=OFF")
            self.conns[db] = con
        self.table_db = {t: db for db, tables in DATABASES.items() for t in tables}

    def append(self, table: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        df.to_sql(table, self.conns[self.table_db[table]], if_exists="append", index=False, chunksize=50_000)

    def close(self):
        for db, con in self.conns.items():
            for table in DATABASES[db]:
                for col in INDEXES.get(table, []):
                    try:
                        con.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_{col} ON {table}({col})")
                    except sqlite3.OperationalError:
                        pass
            con.commit()
            con.close()


class CsvWriter:
    def __init__(self, out_dir: Path):
        self.dir = out_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        self.started = set()

    def append(self, name: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        path = self.dir / f"{name}.csv"
        first = name not in self.started
        df.to_csv(path, mode="w" if first else "a", header=first, index=False)
        self.started.add(name)
