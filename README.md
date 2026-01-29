# SleepLift (Data Engineering Pipeline)

## Architecture explained (Bronze → Silver → Gold)
- **Bronze:** raw CSV exports in `data/raw/` ingested into DuckDB table `raw_events` (idempotent via content-hash `event_id`)
- **Silver:** typed domain tables (`sleep`, `caffeine`, `workout`, `nutrition`) with parsed dates/timestamps
- **Gold:** `daily_features` table + `data/gold/daily_features.csv` for dashboard consumption
- **Quality:** range checks + uniqueness checks; bad rows routed to `dead_rows` instead of crashing

## How to run
```bash
source .venv/bin/activate
python3 src/pipeline/run_all.py
streamlit run src/dashboard.py


