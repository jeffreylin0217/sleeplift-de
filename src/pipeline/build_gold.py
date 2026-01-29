from pathlib import Path
import duckdb

DB_PATH = Path("data/warehouse/sleeplift.duckdb")
OUT_CSV = Path("data/gold/daily_features.csv")

def main():
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))

    # Build a day spine from all tables
    con.execute("""
    CREATE OR REPLACE VIEW day_spine AS
    SELECT DISTINCT day FROM (
        SELECT day FROM sleep
        UNION ALL SELECT day FROM caffeine
        UNION ALL SELECT day FROM workout
        UNION ALL SELECT day FROM nutrition
    ) WHERE day IS NOT NULL;
    """)

    # GOLD daily_features table
    con.execute("""
    CREATE TABLE IF NOT EXISTS daily_features AS
    SELECT * FROM (SELECT 1) WHERE 1=0;
    """)

    con.execute("DROP TABLE IF EXISTS daily_features;")
    con.execute("""
    CREATE TABLE daily_features AS
    SELECT
        d.day,

        -- sleep
        AVG(s.time_in_bed_minutes) AS sleep_minutes,
        COUNT(s.event_id) AS sleep_entries,

        -- caffeine totals
        COALESCE(SUM(c.mg), 0) AS caffeine_mg_total,
        COUNT(c.event_id) AS caffeine_entries,

        -- caffeine after 2pm (DE/analytics-friendly feature)
        COALESCE(SUM(CASE
            WHEN c.ts IS NOT NULL AND EXTRACT('hour' FROM c.ts) >= 14 THEN c.mg
            ELSE 0
        END), 0) AS caffeine_after_2pm_mg,

        -- last caffeine hour
        MAX(CASE
            WHEN c.ts IS NULL THEN NULL
            ELSE EXTRACT('hour' FROM c.ts) + EXTRACT('minute' FROM c.ts)/60.0
        END) AS last_caffeine_hour,

        -- workout
        COALESCE(SUM(w.duration_minutes), 0) AS workout_minutes,
        COUNT(w.event_id) AS workouts,
        AVG(w.rpe) AS avg_rpe,

        -- nutrition
        AVG(n.calories) AS calories,
        AVG(n.protein_g) AS protein_g,
        COUNT(n.event_id) AS nutrition_entries

    FROM day_spine d
    LEFT JOIN sleep s     ON s.day = d.day
    LEFT JOIN caffeine c  ON c.day = d.day
    LEFT JOIN workout w   ON w.day = d.day
    LEFT JOIN nutrition n ON n.day = d.day
    GROUP BY d.day
    ORDER BY d.day;
    """)

    # Export to CSV for Streamlit (serving layer)
    con.execute(f"COPY daily_features TO '{OUT_CSV.as_posix()}' (HEADER, DELIMITER ',');")

    n = con.execute("SELECT COUNT(*) FROM daily_features").fetchone()[0]
    print("BUILD GOLD DONE")
    print(f"  wrote: {OUT_CSV}")
    print(f"  daily_features rows: {n}")

    con.close()

if __name__ == "__main__":
    main()
