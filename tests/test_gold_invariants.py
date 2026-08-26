from pathlib import Path

import pandas as pd

GOLD = Path("data/gold/daily_features.csv")


def test_gold_file_exists():
    assert GOLD.exists(), "Run: python3 src/pipeline/run_all.py"


def test_one_row_per_day():
    df = pd.read_csv(GOLD)
    assert "day" in df.columns, "daily_features must have a day column"
    assert df["day"].nunique() == len(df), "daily_features should have exactly one row per day"


def test_no_negative_core_metrics():
    df = pd.read_csv(GOLD)
    nonnegative_columns = [
        "sleep_minutes",
        "caffeine_mg_total",
        "caffeine_after_2pm_mg",
        "workout_minutes",
        "workouts",
        "calories",
        "protein_g",
    ]
    for col in nonnegative_columns:
        if col in df.columns:
            assert (df[col].fillna(0) >= 0).all(), f"{col} has negative values"


def test_decision_flags_are_boolean_like():
    df = pd.read_csv(GOLD)
    for col in ["low_sleep_flag", "late_caffeine_flag", "high_caffeine_flag"]:
        if col in df.columns:
            values = set(df[col].dropna().astype(str).str.lower())
            assert values.issubset({"true", "false", "1", "0"}), f"{col} should be boolean-like"
