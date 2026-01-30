[![CI](https://github.com/jeffreylin0217/sleeplift-de/actions/workflows/ci.yml/badge.svg)](https://github.com/jeffreylin0217/sleeplift-de/actions/workflows/ci.yml)

# SleepLift-DE (Data Engineering Pipeline)

A personal analytics batch ELT pipeline that ingests raw CSV exports (sleep, caffeine, workout, nutrition), loads them into DuckDB, transforms them into typed domain tables, and produces a daily-grain feature mart (`daily_features`) consumed by a Streamlit dashboard.

## Key Features 
-Bronze→Silver→Gold batch ELT pipeline (Python, DuckDB) producing a daily-grain feature mart (daily_features) powering a Streamlit dashboard.
-Idempotent ingestion via deterministic content-hash event_id plus data-quality checks (range, uniqueness) quarantining invalid records in dead_rows.
-GitHub Actions CI runs run_all.py to rebuild Gold and executes pytest on every push and pull request.

## Quick Start
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 src/pipeline/run_all.py
streamlit run src/dashboard.py
```
## Architecture (Bronze → Silver → Gold)
- **Bronze:** raw CSV exports in `data/raw/` ingested into DuckDB table `raw_events` (idempotent via content-hash `event_id`)
- **Silver:** typed domain tables (`sleep`, `caffeine`, `workout`, `nutrition`) with parsed dates/timestamps
- **Gold:** `daily_features` table + `data/gold/daily_features.csv` for dashboard consumption
- **Quality:** range checks + uniqueness checks; invalid rows routed to `dead_rows` instead of crashing

## Repository layout
- `src/pipeline/ingest.py` — load raw CSVs into DuckDB (`raw_events`) with idempotent keys
- `src/pipeline/transform.py` — build typed Silver tables
- `src/pipeline/build_gold.py` — build Gold `daily_features` + CSV export
- `src/pipeline/quality.py` — validations + quarantine
- `src/pipeline/run_all.py` — end-to-end pipeline runner
- `src/dashboard.py` — Streamlit dashboard
- `tests/` — pytest checks for Gold invariants
- `docs/data_dictionary.md` — table/column definitions

## How to run (local)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 src/pipeline/run_all.py
Streamlit run src/dashboard.py

```
## Development & tests
```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
