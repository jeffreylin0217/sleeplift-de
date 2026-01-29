from pathlib import Path
import duckdb

DB_PATH = Path("data/warehouse/sleeplift.duckdb")

def main():
    con = duckdb.connect(str(DB_PATH))

    # Helper: parse date and time
    # We keep both DATE (day grain) and TIMESTAMP when available.
    con.execute("""
    CREATE OR REPLACE VIEW v_raw AS
    SELECT
        event_id,
        source_file,
        lower(trim(type)) AS type,
        date_raw,
        time_raw,
        field1, field2, field3,
        notes,
        try_strptime(date_raw, '%Y-%m-%d') AS date_iso,
        try_strptime(date_raw, '%m/%d/%y') AS date_mdy_short,
        try_strptime(date_raw, '%m/%d/%Y') AS date_mdy_long
    FROM raw_events;
    """)

    # Canonical day as DATE
    con.execute("""
    CREATE OR REPLACE VIEW v_raw2 AS
    SELECT
        *,
        COALESCE(CAST(date_iso AS DATE), CAST(date_mdy_short AS DATE), CAST(date_mdy_long AS DATE)) AS day
    FROM v_raw;
    """)

    # Canonical timestamp when time is provided (best effort)
    # time formats like "6:30 AM" or "8:48 PM"
    con.execute("""
    CREATE OR REPLACE VIEW v_raw3 AS
    SELECT
        *,
        CASE
          WHEN day IS NULL THEN NULL
          WHEN time_raw IS NULL OR trim(time_raw) = '' THEN NULL
          ELSE try_strptime(CAST(day AS VARCHAR) || ' ' || replace(time_raw, ' ', ' '), '%Y-%m-%d %I:%M %p')
        END AS ts
    FROM v_raw2;
    """)

    # SILVER: sleep
    con.execute("""
    CREATE TABLE IF NOT EXISTS sleep (
        event_id TEXT PRIMARY KEY,
        day DATE,
        time_in_bed_minutes INTEGER,
        notes TEXT
    );
    """)
    con.execute("""
    INSERT INTO sleep
    SELECT
        event_id,
        day,
        CAST(try_cast(field1 AS DOUBLE) AS INTEGER) AS time_in_bed_minutes,
        notes
    FROM v_raw3
    WHERE type = 'sleep' AND day IS NOT NULL
    ON CONFLICT(event_id) DO UPDATE SET
        day=excluded.day,
        time_in_bed_minutes=excluded.time_in_bed_minutes,
        notes=excluded.notes;
    """)

    # SILVER: caffeine
    con.execute("""
    CREATE TABLE IF NOT EXISTS caffeine (
        event_id TEXT PRIMARY KEY,
        day DATE,
        ts TIMESTAMP,
        mg DOUBLE,
        source TEXT
    );
    """)
    con.execute("""
    INSERT INTO caffeine
    SELECT
        event_id,
        day,
        ts,
        try_cast(field1 AS DOUBLE) AS mg,
        field2 AS source
    FROM v_raw3
    WHERE type = 'caffeine' AND day IS NOT NULL
    ON CONFLICT(event_id) DO UPDATE SET
        day=excluded.day,
        ts=excluded.ts,
        mg=excluded.mg,
        source=excluded.source;
    """)

    # SILVER: workout
    con.execute("""
    CREATE TABLE IF NOT EXISTS workout (
        event_id TEXT PRIMARY KEY,
        day DATE,
        ts TIMESTAMP,
        workout_type TEXT,
        duration_minutes DOUBLE,
        rpe DOUBLE,
        notes TEXT
    );
    """)
    con.execute("""
    INSERT INTO workout
    SELECT
        event_id,
        day,
        ts,
        field1 AS workout_type,
        try_cast(field2 AS DOUBLE) AS duration_minutes,
        try_cast(field3 AS DOUBLE) AS rpe,
        notes
    FROM v_raw3
    WHERE type = 'workout' AND day IS NOT NULL
    ON CONFLICT(event_id) DO UPDATE SET
        day=excluded.day,
        ts=excluded.ts,
        workout_type=excluded.workout_type,
        duration_minutes=excluded.duration_minutes,
        rpe=excluded.rpe,
        notes=excluded.notes;
    """)

    # SILVER: nutrition
    con.execute("""
    CREATE TABLE IF NOT EXISTS nutrition (
        event_id TEXT PRIMARY KEY,
        day DATE,
        calories DOUBLE,
        protein_g DOUBLE
    );
    """)
    con.execute("""
    INSERT INTO nutrition
    SELECT
        event_id,
        day,
        try_cast(field1 AS DOUBLE) AS calories,
        try_cast(field2 AS DOUBLE) AS protein_g
    FROM v_raw3
    WHERE type = 'nutrition' AND day IS NOT NULL
    ON CONFLICT(event_id) DO UPDATE SET
        day=excluded.day,
        calories=excluded.calories,
        protein_g=excluded.protein_g;
    """)

    print("TRANSFORM DONE")
    for t in ["sleep","caffeine","workout","nutrition"]:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n} rows")

    con.close()

if __name__ == "__main__":
    main()
