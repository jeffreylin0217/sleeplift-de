import pandas as pd
import streamlit as st
from pathlib import Path
from math import sqrt

DATA = Path("data/gold/daily_features.csv")

def pearson(x, y):
    xy = pd.concat([x, y], axis=1).dropna()
    if len(xy) < 3:
        return None
    x = xy.iloc[:, 0].astype(float)
    y = xy.iloc[:, 1].astype(float)
    mx, my = x.mean(), y.mean()
    num = ((x - mx) * (y - my)).sum()
    den = sqrt(((x - mx) ** 2).sum() * ((y - my) ** 2).sum())
    if den == 0:
        return None
    return num / den

st.set_page_config(page_title="SleepLift DE Dashboard", layout="wide")
st.title("SleepLift (Data Engineering Pipeline)")

if not DATA.exists():
    st.error("Missing data/gold/daily_features.csv")
    st.code("source .venv/bin/activate\npython src/pipeline/run_all.py")
    st.stop()

df = pd.read_csv(DATA)
df["day"] = pd.to_datetime(df["day"], errors="coerce")
df = df.dropna(subset=["day"]).sort_values("day")

st.subheader("Pipeline Output (Gold)")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Days", int(df["day"].nunique()))
c2.metric("Avg sleep (min)", "N/A" if df["sleep_minutes"].isna().all() else f"{df['sleep_minutes'].mean():.0f}")
c3.metric("Avg caffeine (mg)", f"{df['caffeine_mg_total'].mean():.0f}")
c4.metric("Total workouts", int(df["workouts"].sum()))

st.subheader("Trends")
left, right = st.columns(2)
with left:
    st.line_chart(df.set_index("day")[["sleep_minutes", "workout_minutes"]])
with right:
    st.line_chart(df.set_index("day")[["caffeine_mg_total", "caffeine_after_2pm_mg"]])

st.subheader("Correlations (need ≥ 3 days)")
r1 = pearson(df["caffeine_after_2pm_mg"], df["sleep_minutes"])
r2 = pearson(df["workout_minutes"], df["sleep_minutes"])
r3 = pearson(df["last_caffeine_hour"], df["sleep_minutes"])

def fmt(r):
    return "N/A" if r is None else f"{r:.2f}"

st.write(f"**Caffeine after 2pm → sleep minutes:** {fmt(r1)}")
st.write(f"**Workout minutes → sleep minutes:** {fmt(r2)}")
st.write(f"**Last caffeine hour → sleep minutes:** {fmt(r3)}")

st.subheader("Gold table preview")
st.dataframe(df.sort_values("day", ascending=False), use_container_width=True)
