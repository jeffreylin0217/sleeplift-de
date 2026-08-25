from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb
import pandas as pd

RAW_DIR = Path("data/raw")
DB_PATH = Path("data/warehouse/sleeplift.duckdb")

CANONICAL_COLUMNS = ["type", "date", "time", "field1", "field2", "field3", "notes"]


def clean(value) -> str:
    """Convert missing values to blank strings so hashing is stable."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def make_event_id(row: pd.Series) -> str:
    """Create a deterministic ID from the normalized row contents."""
    parts = [clean(row.get(col, "")).lower() if col == "type" else clean(row.get(col, "")) for col in CANONICAL_COLUMNS]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def split_timestamp(value: str) -> tuple[str, str]:
    """Split a timestamp string into date and time strings when possible."""
    ts = pd.to_datetime(value, errors="coerce")
    if pd.isna(ts):
        return clean(value), ""
    return ts.strftime("%Y-%m-%d"), ts.strftime("%I:%M %p")


def normalize_file(path: Path) -> tuple[pd.DataFrame, list[str]]:
    """
    Convert either the current per-domain demo CSVs or the older unified CSV
    into the shared raw_events shape used by the rest of the pipeline.
    """
    df = pd.read_csv(path)
    lower_cols = {c.lower().strip(): c for c in df.columns}
    name = path.stem.lower()
    issues: list[str] = []

    # Older unified export format: type,date,time,field1,field2,field3,notes
    if all(col in lower_cols for col in CANONICAL_COLUMNS):
        out = pd.DataFrame({col: df[lower_cols[col]] for col in CANONICAL_COLUMNS})
        return out, issues

    rows: list[dict[str, str]] = []

    if name == "sleep" and {"date", "sleep_minutes"}.issubset(lower_cols):
        for _, r in df.iterrows():
            rows.append({
                "type": "sleep",
                "date": clean(r[lower_cols["date"]]),
                "time": "",
                "field1": clean(r[lower_cols["sleep_minutes"]]),
                "field2": "",
                "field3": "",
                "notes": clean(r.get(lower_cols.get("notes", ""), "")),
            })

    elif name == "caffeine" and {"timestamp", "caffeine_mg"}.issubset(lower_cols):
        for _, r in df.iterrows():
            date, time = split_timestamp(clean(r[lower_cols["timestamp"]]))
            rows.append({
                "type": "caffeine",
                "date": date,
                "time": time,
                "field1": clean(r[lower_cols["caffeine_mg"]]),
                "field2": clean(r.get(lower_cols.get("source", ""), "")),
                "field3": "",
                "notes": clean(r.get(lower_cols.get("notes", ""), "")),
            })

    elif name == "workout" and {"date", "duration_minutes"}.issubset(lower_cols):
        for _, r in df.iterrows():
            rows.append({
                "type": "workout",
                "date": clean(r[lower_cols["date"]]),
                "time": clean(r.get(lower_cols.get("time", ""), "")),
                "field1": clean(r.get(lower_cols.get("workout_type", ""), "")),
                "field2": clean(r[lower_cols["duration_minutes"]]),
                "field3": clean(r.get(lower_cols.get("rpe", ""), "")),
                "notes": clean(r.get(lower_cols.get("notes", ""), "")),
            })

    elif name == "nutrition" and {"date", "calories", "protein_g"}.issubset(lower_cols):
        for _, r in df.iterrows():
            rows.append({
                "type": "nutrition",
                "date": clean(r[lower_cols["date"]]),
                "time": "",
                "field1": clean(r[lower_cols["calories"]]),
                "field2": clean(r[lower_cols["protein_g"]]),
                "field3": "",
                "notes": clean(r.get(lower_cols.get("notes", ""), "")),
            })

    else:
        issues.append(f"Unsupported columns in {path.name}: {list(df.columns)}")

    return pd.DataFrame(rows, columns=CANONICAL_COLUMNS), issues


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(f for f in RAW_DIR.glob("*.csv") if f.is_file())
    if not files:
        raise FileNotFoundError(
            f"No CSV files found in {RAW_DIR}. Copy demo files with: cp data/raw/sample/*.csv data/raw/"
        )

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
    total_quarantined = 0
    before_total = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]

    for path in files:
        normalized, issues = normalize_file(path)

        for issue in issues:
            con.execute(
                "INSERT INTO dead_rows VALUES (NULL, ?, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)",
                [path.name, issue],
            )
            total_quarantined += 1

        if normalized.empty:
            continue

        total_read += len(normalized)
        normalized = normalized.fillna("")

        bad_mask = (
            normalized["type"].astype(str).str.strip().eq("")
            | normalized["date"].astype(str).str.strip().eq("")
        )
        bad = normalized[bad_mask].copy()
        good = normalized[~bad_mask].copy()

        if not bad.empty:
            dead_payload = []
            for _, r in bad.iterrows():
                dead_payload.append([
                    None,
                    path.name,
                    "Missing type or date",
                    r["type"],
                    r["date"],
                    r["time"],
                    r["field1"],
                    r["field2"],
                    r["field3"],
                    r["notes"],
                ])
            con.executemany("INSERT INTO dead_rows VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", dead_payload)
            total_quarantined += len(dead_payload)

        if good.empty:
            continue

        good["event_id"] = good.apply(make_event_id, axis=1)

        insert_payload = []
        for _, r in good.iterrows():
            insert_payload.append([
                r["event_id"],
                path.name,
                clean(r["type"]).lower(),
                clean(r["date"]),
                clean(r["time"]),
                clean(r["field1"]),
                clean(r["field2"]),
                clean(r["field3"]),
                clean(r["notes"]),
            ])

        con.executemany(
            """
            INSERT INTO raw_events
            (event_id, source_file, type, date_raw, time_raw, field1, field2, field3, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO NOTHING
            """,
            insert_payload,
        )

    after_total = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    dead_total = con.execute("SELECT COUNT(*) FROM dead_rows").fetchone()[0]

    print("INGEST DONE")
    print(f"  files: {len(files)}")
    print(f"  normalized_rows_read: {total_read}")
    print(f"  rows_inserted_new: {after_total - before_total}")
    print(f"  raw_events_total: {after_total}")
    print(f"  rows_quarantined_this_run: {total_quarantined}")
    print(f"  dead_rows_total: {dead_total}")

    con.close()


if __name__ == "__main__":
    main()
