import hashlib
from pathlib import Path
import pandas as pd
import duckdb

RAW_DIR = Path("data/raw")
DB_PATH = Path("data/warehouse/sleeplift.duckdb")

REQUIRED_COLS = ["type","date","time","field1","field2","field3","notes"]

def make_event_id(row) -> str:
    s = "|".join([
        str(row.get("type","")).strip().lower(),
        str(row.get("date","")).strip(),
        str(row.get("time","")).strip(),
        str(row.get("field1","")).strip(),
        str(row.get("field2","")).strip(),
        str(row.get("field3","")).strip(),
        str(row.get("notes","")).strip(),
    ])
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(RAW_DIR.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW_DIR}. Put exports in data/raw/*.csv")

    con = duckdb.connect(str(DB_PATH))

    con.execute("""
    CREATE TABLE IF NOT EXISTS raw_events (
        event_id TEXT PRIMARY KEY,
        source_file TEXT,
        type TEXT,
        date_raw TEXT,
        time_raw TEXT,
        field1 TEXT,
        field2 TEXT,
        field3 TEXT,
        notes TEXT
    );
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS dead_rows (
        dead_id BIGINT,
        source_file TEXT,
        reason TEXT,
        type TEXT,
        date_raw TEXT,
        time_raw TEXT,
        field1 TEXT,
        field2 TEXT,
        field3 TEXT,
        notes TEXT
    );
    """)

    total_read = 0
    total_dead = 0

    before_total = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]

    for f in files:
        df = pd.read_csv(f)

        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            con.execute("""
                INSERT INTO dead_rows VALUES
                (NULL, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)
            """, [f.name, f"Missing columns: {missing}"])
            total_dead += 1
            continue

        total_read += len(df)

        for c in REQUIRED_COLS:
            df[c] = df[c].astype("string")

        bad_mask = (
            df["type"].isna() | (df["type"].str.strip() == "") |
            df["date"].isna() | (df["date"].str.strip() == "")
        )

        bad = df[bad_mask].copy()
        good = df[~bad_mask].copy()

        if len(bad) > 0:
            dead_payload = []
            for _, r in bad.iterrows():
                dead_payload.append([
                    None, f.name, "Missing type or date",
                    r["type"], r["date"], r["time"],
                    r["field1"], r["field2"], r["field3"], r["notes"]
                ])
            con.executemany(
                "INSERT INTO dead_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                dead_payload
            )
            total_dead += len(dead_payload)

        if len(good) == 0:
            continue

        good["event_id"] = good.apply(make_event_id, axis=1)

        insert_payload = []
        for _, r in good.iterrows():
            insert_payload.append([
                r["event_id"], f.name,
                str(r["type"]).strip().lower(),
                r["date"], r["time"],
                r["field1"], r["field2"], r["field3"], r["notes"]
            ])

        con.executemany("""
            INSERT INTO raw_events
            (event_id, source_file, type, date_raw, time_raw, field1, field2, field3, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO NOTHING
        """, insert_payload)

    after_total = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    inserted_new = after_total - before_total

    raw_count = after_total
    dead_count = con.execute("SELECT COUNT(*) FROM dead_rows").fetchone()[0]

    print("INGEST DONE")
    print(f"  files: {len(files)}")
    print(f"  rows_read: {total_read}")
    print(f"  rows_inserted_new: {inserted_new}")
    print(f"  raw_events_total: {raw_count}")
    print(f"  dead_rows_total: {dead_count}")

    con.close()

if __name__ == "__main__":
    main()
