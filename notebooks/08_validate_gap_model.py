from pathlib import Path
import numpy as np
import pandas as pd

INTERIM = Path("data/interim")
modis = pd.read_parquet(INTERIM / "modis_all.parquet")
viirs = pd.read_parquet(INTERIM / "viirs_all.parquet")
modis = modis[(modis["type"] == 0) & (pd.to_numeric(modis["confidence"], errors="coerce") >= 30)]
viirs = viirs[(viirs["type"] == 0) & (viirs["confidence"] != "l")]
df = pd.concat([modis, viirs], ignore_index=True)
df = df[df["daynight"] == "D"].copy()
ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
df["year"], df["month"] = ist.dt.year, ist.dt.month
df["hour"] = ist.dt.hour + ist.dt.minute / 60

s = df[df["month"].isin([10, 11])]
aq, sn = s[s["satellite"] == "Aqua"], s[s["satellite"] == "SNPP"]
t = pd.DataFrame({
    "gap_h": aq.groupby("year")["hour"].median() - sn.groupby("year")["hour"].median(),
    "count_ratio": sn.groupby("year").size() / aq.groupby("year").size(),
    "frp_ratio": sn.groupby("year")["frp"].sum() / aq.groupby("year")["frp"].sum(),
})
COLS = ["count_ratio", "frp_ratio"]


def fit(train, col):
    k, a = np.polyfit(train["gap_h"], np.log(train[col]), 1)
    return a, k


rows = []
for yr in t.index:  # leave one year out
    train = t.drop(yr)
    row = {"year": yr}
    for col in COLS:
        a, k = fit(train, col)
        pred = np.exp(a + k * t.loc[yr, "gap_h"])
        row[col + "_err_%"] = round(100 * (pred / t.loc[yr, col] - 1), 1)
    rows.append(row)
loo = pd.DataFrame(rows).set_index("year")
print("Leave-one-year-out error (predicted vs actual, %):")
print(loo)
print("\nMedian absolute error (%):", loo.abs().median().round(1).to_dict())

print("\nTrain on 2012-2023 only, predict 2024 and 2025:")
train = t.loc[:2023]
for col in COLS:
    a, k = fit(train, col)
    for yr in (2024, 2025):
        pred = np.exp(a + k * t.loc[yr, "gap_h"])
        print(f"  {col} {yr}: predicted {pred:.2f}, actual {t.loc[yr, col]:.2f}")