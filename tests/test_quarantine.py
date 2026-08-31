from pathlib import Path
import subprocess
import sys

import duckdb


REPO_ROOT = Path(__file__).resolve().parents[1]
INGEST_SCRIPT = REPO_ROOT / "src" / "pipeline" / "ingest.py"


def test_unsupported_csv_is_quarantined(tmp_path):
    """
    Verify that malformed/unsupported CSV input is routed to dead_rows
    instead of entering the clean raw_events table.
    """

    raw_dir = tmp_path / "data" / "raw"
    warehouse_dir = tmp_path / "data" / "warehouse"

    raw_dir.mkdir(parents=True)
    warehouse_dir.mkdir(parents=True)

    # Deliberately unsupported schema.
    bad_csv = raw_dir / "malformed.csv"
    bad_csv.write_text(
        "unexpected_column,another_column\n"
        "bad,value\n",
        encoding="utf-8",
    )

    # Run the real ingestion code, but inside the temporary directory.
    # Because SleepLift uses relative data paths, this creates a completely
    # isolated temporary DuckDB warehouse and does not touch real project data.
    result = subprocess.run(
        [sys.executable, str(INGEST_SCRIPT)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "Ingestion failed unexpectedly.\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    db_path = warehouse_dir / "sleeplift.duckdb"

    assert db_path.exists(), "Ingestion did not create the DuckDB warehouse"

    con = duckdb.connect(str(db_path), read_only=True)

    try:
        dead_rows = con.execute(
            "SELECT COUNT(*) FROM dead_rows"
        ).fetchone()[0]

        raw_events = con.execute(
            "SELECT COUNT(*) FROM raw_events"
        ).fetchone()[0]
    finally:
        con.close()

    # The malformed file should be recorded by the quarantine mechanism.
    assert dead_rows >= 1, (
        "Malformed input was not recorded in dead_rows"
    )

    # It must never enter the clean Bronze event table.
    assert raw_events == 0, (
        "Malformed input incorrectly entered raw_events"
    )
