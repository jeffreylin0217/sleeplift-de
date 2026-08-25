# SleepLift-DE Data Dictionary

## Bronze layer

### `raw_events`

Purpose: source-of-truth table for normalized raw events from CSV exports.

Grain: one row per raw sleep, caffeine, workout, or nutrition event.

| Column | Meaning |
|---|---|
| `event_id` | Deterministic SHA-256 content hash used to prevent duplicate inserts on reruns |
| `source_file` | CSV file the row came from |
| `type` | Event type: `sleep`, `caffeine`, `workout`, or `nutrition` |
| `date_raw` | Original date string from the export |
| `time_raw` | Original time string when available |
| `field1`, `field2`, `field3` | Flexible raw payload fields used before typing the record |
| `notes` | Optional notes from the export |

### `dead_rows`

Purpose: rows that could not safely enter the clean tables.

Examples: missing required date/type or unsupported CSV columns.

## Silver layer

### `sleep`

Grain: one row per sleep log.

| Column | Meaning |
|---|---|
| `event_id` | Source event key |
| `day` | Calendar date |
| `time_in_bed_minutes` | Minutes slept or time in bed from the sleep log |
| `notes` | Optional notes |

### `caffeine`

Grain: one row per caffeine log.

| Column | Meaning |
|---|---|
| `event_id` | Source event key |
| `day` | Calendar date |
| `ts` | Timestamp when available |
| `mg` | Caffeine amount in milligrams |
| `source` | Coffee, tea, energy drink, pre-workout, etc. |

### `workout`

Grain: one row per workout log.

| Column | Meaning |
|---|---|
| `event_id` | Source event key |
| `day` | Calendar date |
| `ts` | Timestamp when available |
| `workout_type` | Lift, cardio, walk, sport, etc. |
| `duration_minutes` | Workout duration in minutes |
| `rpe` | Rating of perceived exertion when available |
| `notes` | Optional notes |

### `nutrition`

Grain: one row per nutrition log.

| Column | Meaning |
|---|---|
| `event_id` | Source event key |
| `day` | Calendar date |
| `calories` | Daily calories |
| `protein_g` | Protein in grams |

## Gold layer

### `daily_features`

Purpose: analytics-ready feature mart used by the Streamlit dashboard.

Grain: one row per calendar day.

| Column | Meaning |
|---|---|
| `day` | Calendar date |
| `sleep_minutes` | Average sleep/time-in-bed minutes for the day |
| `caffeine_mg_total` | Total caffeine logged that day |
| `caffeine_after_2pm_mg` | Caffeine logged at or after 2 PM |
| `last_caffeine_hour` | Last caffeine time as a decimal hour |
| `workout_minutes` | Total workout minutes |
| `workouts` | Number of workout logs |
| `avg_rpe` | Average workout intensity |
| `calories` | Average calories logged |
| `protein_g` | Average protein logged |
| `low_sleep_flag` | `TRUE` when sleep is under 6 hours |
| `late_caffeine_flag` | `TRUE` when caffeine after 2 PM is logged |
| `high_caffeine_flag` | `TRUE` when daily caffeine is over 300 mg |
