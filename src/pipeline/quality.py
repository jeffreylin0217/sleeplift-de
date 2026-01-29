from pathlib import Path
import duckdb
import sys

DB_PATH = Path("data/warehouse/sleeplift.duckdb")

def fail(msg):
    print(f"QUALITY FAIL: {msg}")
    sys.exit(1)

def main():
    con = duckdb.connect(str(DB_PATH))

    # Must have gold table
    exists = con.execute("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name='daily_features';
    """).fetchone()[0]
    if exists == 0:
        fail("daily_features table missing. Run build_gold.py")

    # Unique day
    dup_days = con.execute("""
        SELECT COUNT(*) FROM (
            SELECT day, COUNT(*) c FROM daily_features GROUP BY day HAVING c > 1
        );
    """).fetchone()[0]
    if dup_days != 0:
        fail("daily_features has duplicate day rows")

    # Reasonable ranges (adjust as you like)
    bad_sleep = con.execute("""
        SELECT COUNT(*) FROM daily_features
        WHERE sleep_minutes IS NOT NULL AND (sleep_minutes < 120 OR sleep_minutes > 900);
    """).fetchone()[0]
    if bad_sleep > 0:
        fail(f"{bad_sleep} rows have unrealistic sleep_minutes (<120 or >900). Fix input or add cleaning rules.")

    bad_caf = con.execute("""
        SELECT COUNT(*) FROM daily_features
        WHERE caffeine_mg_total < 0 OR caffeine_mg_total > 1200;
    """).fetchone()[0]
    if bad_caf > 0:
        fail(f"{bad_caf} rows have unrealistic caffeine_mg_total (<0 or >1200).")

    bad_workout = con.execute("""
        SELECT COUNT(*) FROM daily_features
        WHERE workout_minutes < 0 OR workout_minutes > 600;
    """).fetchone()[0]
    if bad_workout > 0:
        fail(f"{bad_workout} rows have unrealistic workout_minutes (<0 or >600).")

    # Print pass + stats
    days = con.execute("SELECT COUNT(*) FROM daily_features").fetchone()[0]
    raw = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    dead = con.execute("SELECT COUNT(*) FROM dead_rows").fetchone()[0]

    print("QUALITY PASS")
    print(f"  raw_events: {raw}")
    print(f"  dead_rows:  {dead}")
    print(f"  days:       {days}")

    con.close()

if __name__ == "__main__":
    main()
