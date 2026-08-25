from pathlib import Path

import duckdb

DB_PATH = Path("data/warehouse/sleeplift.duckdb")
OUT_CSV = Path("data/gold/daily_features.csv")


def main() -> None:
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    con.execute("""
    CREATE OR REPLACE VIEW day_spine AS
    SELECT DISTINCT day FROM (
        SELECT day FROM sleep
        UNION ALL SELECT day FROM caffeine
        UNION ALL SELECT day FROM workout
        UNION ALL SELECT day FROM nutrition
    )
    WHERE day IS NOT NULL;
    """)

    # Aggregate each domain before joining so multiple caffeine/workout rows on
    # the same day do not accidentally multiply each other.
    con.execute("""
    CREATE OR REPLACE VIEW sleep_daily AS
    SELECT
        day,
        AVG(time_in_bed_minutes) AS sleep_minutes,
        COUNT(event_id) AS sleep_entries
    FROM sleep
    GROUP BY day;
    """)

    con.execute("""
    CREATE OR REPLACE VIEW caffeine_daily AS
    SELECT
        day,
        COALESCE(SUM(mg), 0) AS caffeine_mg_total,
        COUNT(event_id) AS caffeine_entries,
        COALESCE(SUM(CASE
            WHEN ts IS NOT NULL AND EXTRACT('hour' FROM ts) >= 14 THEN mg
            ELSE 0
        END), 0) AS caffeine_after_2pm_mg,
        MAX(CASE
            WHEN ts IS NULL THEN NULL
            ELSE EXTRACT('hour' FROM ts) + EXTRACT('minute' FROM ts) / 60.0
        END) AS last_caffeine_hour
    FROM caffeine
    GROUP BY day;
    """)

    con.execute("""
    CREATE OR REPLACE VIEW workout_daily AS
    SELECT
        day,
        COALESCE(SUM(duration_minutes), 0) AS workout_minutes,
        COUNT(event_id) AS workouts,
        AVG(rpe) AS avg_rpe
    FROM workout
    GROUP BY day;
    """)

    con.execute("""
    CREATE OR REPLACE VIEW nutrition_daily AS
    SELECT
        day,
        AVG(calories) AS calories,
        AVG(protein_g) AS protein_g,
        COUNT(event_id) AS nutrition_entries
    FROM nutrition
    GROUP BY day;
    """)

    con.execute("DROP TABLE IF EXISTS daily_features;")
    con.execute("""
    CREATE TABLE daily_features AS
    SELECT
        d.day,
        s.sleep_minutes,
        COALESCE(s.sleep_entries, 0) AS sleep_entries,
        COALESCE(c.caffeine_mg_total, 0) AS caffeine_mg_total,
        COALESCE(c.caffeine_entries, 0) AS caffeine_entries,
        COALESCE(c.caffeine_after_2pm_mg, 0) AS caffeine_after_2pm_mg,
        c.last_caffeine_hour,
        COALESCE(w.workout_minutes, 0) AS workout_minutes,
        COALESCE(w.workouts, 0) AS workouts,
        w.avg_rpe,
        n.calories,
        n.protein_g,
        COALESCE(n.nutrition_entries, 0) AS nutrition_entries,
        CASE WHEN s.sleep_minutes IS NOT NULL AND s.sleep_minutes < 360 THEN TRUE ELSE FALSE END AS low_sleep_flag,
        CASE WHEN COALESCE(c.caffeine_after_2pm_mg, 0) > 0 THEN TRUE ELSE FALSE END AS late_caffeine_flag,
        CASE WHEN COALESCE(c.caffeine_mg_total, 0) > 300 THEN TRUE ELSE FALSE END AS high_caffeine_flag
    FROM day_spine d
    LEFT JOIN sleep_daily s ON s.day = d.day
    LEFT JOIN caffeine_daily c ON c.day = d.day
    LEFT JOIN workout_daily w ON w.day = d.day
    LEFT JOIN nutrition_daily n ON n.day = d.day
    ORDER BY d.day;
    """)

    con.execute(f"COPY daily_features TO '{OUT_CSV.as_posix()}' (HEADER, DELIMITER ',');")

    rows = con.execute("SELECT COUNT(*) FROM daily_features").fetchone()[0]
    print("BUILD GOLD DONE")
    print(f"  wrote: {OUT_CSV}")
    print(f"  daily_features rows: {rows}")

    con.close()


if __name__ == "__main__":
    main()
