from pathlib import Path

import pandas as pd
import streamlit as st

DATA = Path("data/gold/daily_features.csv")

st.set_page_config(page_title="SleepLift-DE Dashboard", layout="wide")
st.title("SleepLift-DE Dashboard")
st.caption("Gold-layer dashboard built from daily_features.csv")

if not DATA.exists():
    st.error("Missing data/gold/daily_features.csv")
    st.code("cp data/raw/sample/*.csv data/raw/\npython3 src/pipeline/run_all.py")
    st.stop()

df = pd.read_csv(DATA)
df["day"] = pd.to_datetime(df["day"], errors="coerce")
df = df.dropna(subset=["day"]).sort_values("day")

df["sleep_hours"] = df["sleep_minutes"] / 60.0

st.subheader("Gold output summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Days", int(df["day"].nunique()))
col2.metric("Avg sleep", f"{df['sleep_hours'].mean():.1f} hr")
col3.metric("Avg caffeine", f"{df['caffeine_mg_total'].mean():.0f} mg")
col4.metric("Total workouts", int(df["workouts"].sum()))

st.subheader("Daily trends")
left, right = st.columns(2)
with left:
    st.write("Sleep and workout minutes")
    st.line_chart(df.set_index("day")[["sleep_hours", "workout_minutes"]])
with right:
    st.write("Caffeine totals")
    st.line_chart(df.set_index("day")[["caffeine_mg_total", "caffeine_after_2pm_mg"]])

st.subheader("Simple decision-support flags")
flag_columns = [
    "day",
    "sleep_hours",
    "caffeine_mg_total",
    "caffeine_after_2pm_mg",
    "workout_minutes",
    "low_sleep_flag",
    "late_caffeine_flag",
    "high_caffeine_flag",
]
st.dataframe(df[flag_columns].sort_values("day", ascending=False), width='stretch')

st.subheader("Gold table preview")
st.dataframe(df.sort_values("day", ascending=False), width='stretch')
