from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

INTERIM = Path("data/interim")
modis = pd.read_parquet(INTERIM / "modis_all.parquet")
viirs = pd.read_parquet(INTERIM / "viirs_all.parquet")

modis = modis[(modis["type"] == 0) & (pd.to_numeric(modis["confidence"], errors="coerce") >= 30)]
viirs = viirs[(viirs["type"] == 0) & (viirs["confidence"] != "l")]
df = pd.concat([modis, viirs], ignore_index=True)
df = df[df["daynight"] == "D"].copy()

ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
df["year"] = ist.dt.year
df["month"] = ist.dt.month
df["hour"] = ist.dt.hour + ist.dt.minute / 60

s = df[df["month"].isin([10, 11])]
aq = s[s["satellite"] == "Aqua"]
sn = s[s["satellite"] == "SNPP"]

out = pd.DataFrame({
    "gap_h": aq.groupby("year")["hour"].median() - sn.groupby("year")["hour"].median(),
    "count_ratio": sn.groupby("year").size() / aq.groupby("year").size(),
    "frp_ratio": sn.groupby("year")["frp"].sum() / aq.groupby("year")["frp"].sum(),
    "aqua_frp_per_det": aq.groupby("year")["frp"].mean(),
    "snpp_frp_per_det": sn.groupby("year")["frp"].mean(),
})
out["perdet_aqua_over_snpp"] = out["aqua_frp_per_det"] / out["snpp_frp_per_det"]
print("Oct-Nov only, per year:")
print(out.round(2))
print("\nCorrelation:")
print(out[["gap_h", "frp_ratio", "count_ratio", "perdet_aqua_over_snpp"]].corr().round(2))

fig, ax = plt.subplots(figsize=(6.5, 5))
ax.scatter(out["gap_h"], out["frp_ratio"])
for year, r in out.iterrows():
    ax.annotate(str(year), (r["gap_h"], r["frp_ratio"]), textcoords="offset points",
                xytext=(4, 4), fontsize=8)
ax.set(xlabel="Aqua minus S-NPP pass gap (h), Oct-Nov",
       ylabel="FRP ratio S-NPP / Aqua, Oct-Nov",
       title="Each dot is one year")
plt.tight_layout()
plt.savefig("docs/day6_gap_vs_ratio.png", dpi=130)
print("\nsaved docs/day6_gap_vs_ratio.png")