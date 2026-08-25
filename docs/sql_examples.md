# SleepLift-DE SQL Examples

These are simple DuckDB queries that can be run against `data/warehouse/sleeplift.duckdb` after the pipeline runs.

## View daily Gold features

```sql
SELECT *
FROM daily_features
ORDER BY day;
```

## Find days with late caffeine

```sql
SELECT day, caffeine_mg_total, caffeine_after_2pm_mg, sleep_minutes
FROM daily_features
WHERE late_caffeine_flag = TRUE
ORDER BY day;
```

## Average sleep by whether late caffeine happened

```sql
SELECT
    late_caffeine_flag,
    AVG(sleep_minutes) AS avg_sleep_minutes,
    COUNT(*) AS days
FROM daily_features
GROUP BY late_caffeine_flag;
```

## Check event counts by raw source file

```sql
SELECT source_file, COUNT(*) AS rows
FROM raw_events
GROUP BY source_file
ORDER BY rows DESC;
```
