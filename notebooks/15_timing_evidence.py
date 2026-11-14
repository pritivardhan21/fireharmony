"""Timing evidence for Oct-Nov: S-NPP day/night detections, Aqua daytime detections and median
daytime overpass hour (IST) by year. Writes web/public/data/timing_evidence.json. Run from the project root."""
import json
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
s = df[df["month"].isin([10, 11])]


def med(x):
    return None if len(x) == 0 else round(float(x.median()), 2)


rows = []
for y in sorted(int(v) for v in s["year"].unique()):
    g = s[s["year"] == y]
    sn, aq = g[g["satellite"] == "SNPP"], g[g["satellite"] == "Aqua"]
    sd, ad = sn[sn["daynight"] == "D"], aq[aq["daynight"] == "D"]
    rows.append({
        "year": y, "snpp_day": int(len(sd)), "snpp_night": int((sn["daynight"] == "N").sum()),
        "aqua_day": int(len(ad)), "snpp_day_hour": med(sd["hour"]), "aqua_day_hour": med(ad["hour"]),
    })
out = Path("web/public/data/timing_evidence.json")
out.write_text(json.dumps(rows))
print(pd.DataFrame(rows).to_string(index=False))
print("wrote", out)
