from pathlib import Path
import pandas as pd

RAW = Path("data/raw")
INTERIM = Path("data/interim")


def load(tag):
    files = [p for p in RAW.rglob("*.csv") if tag in str(p)]
    print(f"\n{tag} files:", [str(p) for p in files])
    df = pd.concat(
        [pd.read_csv(p, dtype={"acq_time": str, "confidence": str}) for p in files],
        ignore_index=True,
    )
    df["acq_time"] = df["acq_time"].str.zfill(4)
    df["datetime_utc"] = pd.to_datetime(
        df["acq_date"] + " " + df["acq_time"], format="%Y-%m-%d %H%M", utc=True
    )
    df = df.drop_duplicates(subset=["latitude", "longitude", "datetime_utc", "satellite"])
    print("rows:", len(df), "| dates:", df["acq_date"].min(), "->", df["acq_date"].max())
    print("satellite values:", df["satellite"].value_counts().to_dict())
    return df


n20 = load("J1V")
n21 = load("J2V")
n20.to_parquet(INTERIM / "noaa20_all.parquet", index=False)
n21.to_parquet(INTERIM / "noaa21_all.parquet", index=False)

snpp = pd.read_parquet(INTERIM / "viirs_all.parquet")
snpp = snpp[snpp["satellite"] == "SNPP"]


print("\nNOAA-21 columns:", list(n21.columns))


def prep(df, use_type=True):
    keep = (df["confidence"] != "l") & (df["daynight"] == "D")
    if use_type:
        keep &= df["type"] == 0
    df = df[keep].copy()
    ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
    df["year"], df["month"] = ist.dt.year, ist.dt.month
    df["hour"] = ist.dt.hour + ist.dt.minute / 60
    return df


typed = {"SNPP": prep(snpp), "N20": prep(n20)}
untyped = {"SNPP": prep(snpp, use_type=False), "N21": prep(n21, use_type=False)}

print("\nMedian local pass hour (IST) per year, daytime:")
hours = pd.DataFrame({
    "SNPP": typed["SNPP"].groupby("year")["hour"].median(),
    "N20": typed["N20"].groupby("year")["hour"].median(),
    "N21": untyped["N21"].groupby("year")["hour"].median(),
})
print(hours.round(2))


def ratios(a, b, months):
    A = a[a["month"].isin(months)]
    B = b[b["month"].isin(months)]
    return pd.DataFrame({
        "counts": A.groupby("year").size() / B.groupby("year").size(),
        "FRP": A.groupby("year")["frp"].sum() / B.groupby("year")["frp"].sum(),
    })


for label, months in [("whole year", range(1, 13)), ("Oct-Nov", [10, 11])]:
    print(f"\nN20 / SNPP, {label} (vegetation fires only):")
    print(ratios(typed["N20"], typed["SNPP"], months).round(2))
    print(f"\nN21 / SNPP, {label} (no type filter, NRT data):")
    print(ratios(untyped["N21"], untyped["SNPP"], months).dropna().round(2))