from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

RAW = Path("data/raw")
INTERIM = Path("data/interim")
INTERIM.mkdir(parents=True, exist_ok=True)
Path("docs").mkdir(exist_ok=True)


def load(path, sensor):
    df = pd.read_csv(path, dtype={"acq_time": str, "confidence": str})
    df["acq_time"] = df["acq_time"].str.zfill(4)
    df["datetime_utc"] = pd.to_datetime(
        df["acq_date"] + " " + df["acq_time"], format="%Y-%m-%d %H%M", utc=True
    )
    df["sensor"] = sensor
    return df


modis = load(next(RAW.glob("modis/*.csv")), "MODIS")
viirs = load(next(RAW.glob("viirs/*.csv")), "VIIRS")

for name, df in [("MODIS", modis), ("VIIRS", viirs)]:
    print(f"\n=== {name} ===")
    print("rows:", len(df))
    print("dates:", df["acq_date"].min(), "->", df["acq_date"].max())
    print("satellite:", df["satellite"].value_counts().to_dict())
    print("confidence:", df["confidence"].value_counts().head(10).to_dict())
    print("daynight:", df["daynight"].value_counts().to_dict())
    print("type:", df["type"].value_counts().to_dict())
    print(df[["brightness", "frp", "scan", "track"]].describe().round(2))

daily = (
    pd.concat([modis, viirs])
    .groupby(["sensor", "acq_date"])
    .agg(detections=("frp", "size"), total_frp=("frp", "sum"))
    .reset_index()
)
print("\n=== Year totals ===")
print(daily.groupby("sensor")[["detections", "total_frp"]].sum().round(0))

fig, axes = plt.subplots(1, 2, figsize=(14, 4))
for col, ax, title in [
    ("detections", axes[0], "Detections per day"),
    ("total_frp", axes[1], "Total FRP per day (MW)"),
]:
    p = daily.pivot(index="acq_date", columns="sensor", values=col)
    p.index = pd.to_datetime(p.index)
    p.rolling(7, min_periods=1).mean().plot(ax=ax, title=title + " (7-day mean)")
plt.tight_layout()
plt.savefig("docs/day2_compare.png", dpi=130)
print("\nsaved docs/day2_compare.png")

modis.to_parquet(INTERIM / "modis_2024.parquet", index=False)
viirs.to_parquet(INTERIM / "viirs_2024.parquet", index=False)
print("saved parquet files to data/interim")