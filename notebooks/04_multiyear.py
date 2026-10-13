from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

RAW = Path("data/raw")
INTERIM = Path("data/interim")
INTERIM.mkdir(parents=True, exist_ok=True)


def load(folders, sensor):
    frames = []
    for folder in folders:
        for f in folder.rglob("*.csv"):
            frames.append(pd.read_csv(f, dtype={"acq_time": str, "confidence": str}))
    df = pd.concat(frames, ignore_index=True)
    df["acq_time"] = df["acq_time"].str.zfill(4)
    df["datetime_utc"] = pd.to_datetime(
        df["acq_date"] + " " + df["acq_time"], format="%Y-%m-%d %H%M", utc=True
    )
    df = df.drop_duplicates(subset=["latitude", "longitude", "datetime_utc", "satellite"])
    df["sensor"] = sensor
    return df


modis = load(sorted(RAW.glob("modis*")), "MODIS")
viirs = load(sorted(RAW.glob("viirs*")), "VIIRS")
print("MODIS rows:", len(modis), "| VIIRS rows:", len(viirs))
modis.to_parquet(INTERIM / "modis_all.parquet", index=False)
viirs.to_parquet(INTERIM / "viirs_all.parquet", index=False)

# same filters as before: vegetation fires, daytime, drop low-confidence detections
modis = modis[(modis["type"] == 0) & (pd.to_numeric(modis["confidence"], errors="coerce") >= 30)]
viirs = viirs[(viirs["type"] == 0) & (viirs["confidence"] != "l")]
df = pd.concat([modis, viirs], ignore_index=True)
df = df[df["daynight"] == "D"].copy()

ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
df["year"] = ist.dt.year
df["month"] = ist.dt.month
df["hour"] = ist.dt.hour + ist.dt.minute / 60

print("\nDaytime detections per year and satellite:")
print(df.pivot_table(index="year", columns="satellite", values="frp", aggfunc="size"))

hours = df.pivot_table(index="year", columns="satellite", values="hour", aggfunc="median")
hours["Aqua-SNPP (h)"] = hours["Aqua"] - hours["SNPP"]
print("\nMedian local pass hour (IST) per year:")
print(hours.round(2))

frp_all = df.pivot_table(index="year", columns="satellite", values="frp", aggfunc="sum")
frp_all["SNPP/Aqua"] = frp_all["SNPP"] / frp_all["Aqua"]
stub = df[df["month"].isin([10, 11])].pivot_table(
    index="year", columns="satellite", values="frp", aggfunc="sum"
)
stub["SNPP/Aqua"] = stub["SNPP"] / stub["Aqua"]
print("\nTotal FRP ratio SNPP/Aqua, whole year:")
print(frp_all["SNPP/Aqua"].round(2))
print("\nTotal FRP ratio SNPP/Aqua, Oct-Nov only (stubble season):")
print(stub["SNPP/Aqua"].round(2))

fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
hours["Aqua-SNPP (h)"].plot(marker="o", ax=ax[0], title="Aqua minus S-NPP pass time (hours)")
frp_all["SNPP/Aqua"].plot(marker="o", ax=ax[1], label="whole year")
stub["SNPP/Aqua"].plot(marker="o", ax=ax[1], label="Oct-Nov")
ax[1].set_title("FRP ratio: S-NPP / Aqua")
ax[1].legend()
plt.tight_layout()
plt.savefig("docs/day5_years.png", dpi=130)
print("\nsaved docs/day5_years.png")