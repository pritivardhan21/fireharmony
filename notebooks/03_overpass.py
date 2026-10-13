from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

INTERIM = Path("data/interim")
modis = pd.read_parquet(INTERIM / "modis_2024.parquet")
viirs = pd.read_parquet(INTERIM / "viirs_2024.parquet")

df = pd.concat([modis, viirs])
df = df[(df["type"] == 0) & (df["daynight"] == "D")].copy()  # daytime vegetation fires
ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
df["hour"] = ist.dt.hour + ist.dt.minute / 60
df["month"] = ist.dt.month

print("Local (IST) overpass hour by satellite, daytime:")
print(df.groupby("satellite")["hour"].describe().round(2))

print("\nMedian local hour by month:")
print(df.pivot_table(index="month", columns="satellite", values="hour", aggfunc="median").round(2))

print("\nMean FRP per detection by month:")
print(df.pivot_table(index="month", columns="satellite", values="frp", aggfunc="mean").round(1))

fig, ax = plt.subplots(figsize=(8, 4.5))
for sat, g in df.groupby("satellite"):
    ax.hist(g["hour"], bins=48, range=(6, 20), alpha=0.5, density=True, label=sat)
ax.set(xlabel="Local time (IST, hours)", ylabel="Share of detections",
       title="When each satellite sees fires (daytime)")
ax.legend()
plt.tight_layout()
plt.savefig("docs/day4_overpass.png", dpi=130)
print("\nsaved docs/day4_overpass.png")