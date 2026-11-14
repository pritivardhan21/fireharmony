"""Day versus night detections by year (S-NPP and Aqua), whole box. Read-only diagnostic."""
from pathlib import Path

import pandas as pd

I = Path("data/interim")
modis = pd.read_parquet(I / "modis_all.parquet")
viirs = pd.read_parquet(I / "viirs_all.parquet")
modis = modis[(modis["type"] == 0) & (pd.to_numeric(modis["confidence"], errors="coerce") >= 30)]
viirs = viirs[(viirs["type"] == 0) & (viirs["confidence"] != "l")]
df = pd.concat([modis, viirs], ignore_index=True)
df = df[df["satellite"].isin(["Aqua", "SNPP"])].copy()
ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
df["year"], df["month"] = ist.dt.year, ist.dt.month
df["hour"] = ist.dt.hour + ist.dt.minute / 60
pd.set_option("display.width", 200)

for sat in ("SNPP", "Aqua"):
    s = df[df["satellite"] == sat]
    for label, d in (("Oct-Nov", s[s["month"].isin([10, 11])]), ("whole year", s)):
        t = d.pivot_table(index="year", columns="daynight", values="frp", aggfunc=["size", "sum"])
        out = pd.DataFrame({
            "day_n": t[("size", "D")], "night_n": t[("size", "N")],
            "night_share_%": 100 * t[("size", "N")] / (t[("size", "D")] + t[("size", "N")]),
            "day_frp": t[("sum", "D")].round(0), "night_frp": t[("sum", "N")].round(0),
        })
        print(f"\n=== {sat}, {label}: detections and FRP by day/night ===")
        print(out.round(2).to_string())
    h = s.groupby(["year", "daynight"])["hour"].median().unstack().round(2)
    print(f"\n{sat} median local overpass hour by year (day D / night N):")
    print(h.to_string())
