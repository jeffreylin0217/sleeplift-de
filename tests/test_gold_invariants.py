import pandas as pd
from pathlib import Path

GOLD = Path("data/gold/daily_features.csv")

def test_gold_file_exists():
    assert GOLD.exists(), "Run: python3 src/pipeline/run_all.py (gold CSV not found)"

def test_one_row_per_day():
    df = pd.read_csv(GOLD)
    assert "day" in df.columns, "gold must have 'day' column"
    # allow day as string or datetime; uniqueness check works either way
    assert df["day"].nunique() == len(df), "gold should have exactly 1 row per day"

def test_no_negative_core_metrics():
    df = pd.read_csv(GOLD)
    # only check columns if they exist (keeps it robust if your schema changes slightly)
    nonneg_cols = [
        "sleep_minutes",
        "caffeine_mg_total",
        "caffeine_after_2pm_mg",
        "workout_minutes",
        "workouts",
        "calories",
        "protein_g",
    ]
    for c in nonneg_cols:
        if c in df.columns:
            assert (df[c].fillna(0) >= 0).all(), f"{c} has negative values"
