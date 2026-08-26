from pathlib import Path
import sys

import duckdb

DB_PATH = Path("data/warehouse/sleeplift.duckdb")


def fail(message: str) -> None:
    print(f"QUALITY FAIL: {message}")
    sys.exit(1)


def main() -> None:
    con = duckdb.connect(str(DB_PATH))

    exists = con.execute("""
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = 'daily_features';
    """).fetchone()[0]
    if exists == 0:
        fail("daily_features table missing. Run src/pipeline/build_gold.py")

    duplicate_days = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT day, COUNT(*) AS n
            FROM daily_features
            GROUP BY day
            HAVING n > 1
        );
    """).fetchone()[0]
    if duplicate_days:
        fail("daily_features should have exactly one row per day")

    duplicate_events = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT event_id, COUNT(*) AS n
            FROM raw_events
            GROUP BY event_id
            HAVING n > 1
        );
    """).fetchone()[0]
    if duplicate_events:
        fail("raw_events has duplicate event_id values")

    bad_sleep = con.execute("""
        SELECT COUNT(*)
        FROM daily_features
        WHERE sleep_minutes IS NOT NULL
          AND (sleep_minutes < 120 OR sleep_minutes > 900);
    """).fetchone()[0]
    if bad_sleep:
        fail(f"{bad_sleep} rows have sleep_minutes outside the expected range of 120-900")

    bad_caffeine = con.execute("""
        SELECT COUNT(*)
        FROM daily_features
        WHERE caffeine_mg_total < 0 OR caffeine_mg_total > 1200;
    """).fetchone()[0]
    if bad_caffeine:
        fail(f"{bad_caffeine} rows have caffeine_mg_total outside the expected range of 0-1200")

    bad_workout = con.execute("""
        SELECT COUNT(*)
        FROM daily_features
        WHERE workout_minutes < 0 OR workout_minutes > 600;
    """).fetchone()[0]
    if bad_workout:
        fail(f"{bad_workout} rows have workout_minutes outside the expected range of 0-600")

    days = con.execute("SELECT COUNT(*) FROM daily_features").fetchone()[0]
    raw = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    dead = con.execute("SELECT COUNT(*) FROM dead_rows").fetchone()[0]

    print("QUALITY PASS")
    print(f"  raw_events:     {raw}")
    print(f"  dead_rows:      {dead}")
    print(f"  daily_features: {days} days")

    con.close()


if __name__ == "__main__":
    main()
