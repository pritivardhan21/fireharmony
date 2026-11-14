from pathlib import Path
import numpy as np
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
df["year"], df["month"] = ist.dt.year, ist.dt.month
df["hour"] = ist.dt.hour + ist.dt.minute / 60

s = df[df["month"].isin([10, 11])]
aq = s[s["satellite"] == "Aqua"]
sn = s[s["satellite"] == "SNPP"]
t = pd.DataFrame({
    "gap_h": aq.groupby("year")["hour"].median() - sn.groupby("year")["hour"].median(),
    "count_ratio": sn.groupby("year").size() / aq.groupby("year").size(),
    "frp_ratio": sn.groupby("year")["frp"].sum() / aq.groupby("year")["frp"].sum(),
})

for col in ["count_ratio", "frp_ratio"]:
    y = np.log(t[col])
    k, a = np.polyfit(t["gap_h"], y, 1)
    fit = a + k * t["gap_h"]
    r2 = 1 - ((y - fit) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    t[col + "_fit"] = np.exp(fit)
    print(f"{col}: ratio at zero gap = {np.exp(a):.2f}; "
          f"each extra hour of gap multiplies it by {np.exp(k):.2f}; R2 = {r2:.2f}")
print()
print(t.round(2))

fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
order = t["gap_h"].sort_values().index
for axis, col in zip(ax, ["count_ratio", "frp_ratio"]):
    axis.scatter(t["gap_h"], t[col])
    axis.plot(t.loc[order, "gap_h"], t.loc[order, col + "_fit"], color="red")
    for yr, r in t.iterrows():
        axis.annotate(str(yr), (r["gap_h"], r[col]), textcoords="offset points",
                      xytext=(3, 3), fontsize=8)
    axis.set(xlabel="Aqua minus S-NPP pass gap (h)", ylabel=col,
             title=col + " vs pass gap (Oct-Nov)")
plt.tight_layout()
plt.savefig("docs/day8_gap_model.png", dpi=130)
print("saved docs/day8_gap_model.png")