# SleepLift-DE Data Dictionary

## Bronze
### raw_events
- Purpose: raw ingested events from CSV (auditable source-of-truth)
- Key columns (typical):
  - event_id: deterministic unique id (content hash)
  - type: sleep/caffeine/workout/nutrition
  - date/time: raw strings from export
  - field1/field2/field3/notes: raw payload

## Silver (typed domain tables)
### sleep
- Grain: 1 row per sleep log
- Columns (example):
  - day (DATE)
  - sleep_minutes (INT): minutes slept/time-in-bed depending on your logging

### caffeine
- Grain: 1 row per caffeine log
- Columns:
  - ts (TIMESTAMP)
  - caffeine_mg (INT)
  - source (TEXT): coffee/energyDrink/preworkout

### workout
- Grain: 1 row per workout log
- Columns:
  - ts (TIMESTAMP)
  - workout_type (TEXT): Lift/Cardio/Sport
  - minutes (INT)
  - rpe (INT) or intensity proxy

### nutrition
- Grain: 1 row per day (or per log, depending on your input)
- Columns:
  - day (DATE)
  - calories (INT)
  - protein_g (INT)

## Gold
### daily_features
- Grain: 1 row per day
- Purpose: analytics-ready daily KPIs for dashboard consumption
- Common columns (update to match your actual output):
  - day
  - sleep_minutes
  - caffeine_mg_total
  - caffeine_after_2pm_mg
  - last_caffeine_hour
  - workout_minutes
  - workouts
  - calories
  - protein_g
