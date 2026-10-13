from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

INTERIM = Path("data/interim")
FULL = pd.date_range("2024-01-01", "2024-12-31", freq="D")

modis = pd.read_parquet(INTERIM / "modis_2024.parquet")
viirs = pd.read_parquet(INTERIM / "viirs_2024.parquet")


def prep(df):
    df = df[df["type"] == 0].copy()  # presumed vegetation fires only
    ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
    df["local_date"] = ist.dt.tz_localize(None).dt.normalize()
    return df[(df["local_date"] >= "2024-01-01") & (df["local_date"] <= "2024-12-31")]


modis_f = prep(modis)
modis_f = modis_f[pd.to_numeric(modis_f["confidence"], errors="coerce") >= 30]
viirs_f = prep(viirs)
viirs_f = viirs_f[viirs_f["confidence"] != "l"]
print("rows kept  MODIS:", len(modis_f), "of", len(modis), "| VIIRS:", len(viirs_f), "of", len(viirs))


def daily(df):
    g = df.groupby("local_date")["frp"].agg(detections="size", frp="sum")
    return g.reindex(FULL, fill_value=0)


def compare(x, y):
    lr = stats.linregress(x, y)
    return {
        "VIIRS/MODIS total": round(y.sum() / x.sum(), 2),
        "pearson r": round(lr.rvalue, 3),
        "spearman": round(stats.spearmanr(x, y)[0], 3),
        "slope": round(lr.slope, 2),
        "intercept": round(lr.intercept, 1),
    }


variants = {
    "Aqua only": modis_f[modis_f["satellite"] == "Aqua"],
    "Terra only": modis_f[modis_f["satellite"] == "Terra"],
    "Aqua+Terra": modis_f,
}
v = daily(viirs_f)

rows = []
for name, df in variants.items():
    m = daily(df)
    for field in ["detections", "frp"]:
        for freq, label in [("D", "daily"), ("W", "weekly")]:
            x = m[field] if freq == "D" else m[field].resample("W").sum()
            y = v[field] if freq == "D" else v[field].resample("W").sum()
            rows.append({"MODIS": name, "metric": field, "scale": label, **compare(x, y)})
print("\n", pd.DataFrame(rows).to_string(index=False))

aq = daily(variants["Aqua only"])
monthly = pd.DataFrame({
    "aqua_frp": aq["frp"].resample("MS").sum(),
    "viirs_frp": v["frp"].resample("MS").sum(),
})
monthly["ratio"] = (monthly["viirs_frp"] / monthly["aqua_frp"]).round(2)
print("\nMonthly FRP, VIIRS vs Aqua:\n", monthly.round(0).assign(ratio=monthly["ratio"]))

print("\nMODIS last 8 days with data:\n", daily(modis_f)["detections"].replace(0, pd.NA).dropna().tail(8))
print("MODIS days with zero detections:", int((daily(modis_f)["detections"] == 0).sum()))

fig, ax = plt.subplots(1, 2, figsize=(13, 4.5))
wx, wy = aq["frp"].resample("W").sum(), v["frp"].resample("W").sum()
ax[0].scatter(wx, wy, s=18)
lr = stats.linregress(wx, wy)
ax[0].plot(wx, lr.intercept + lr.slope * wx, color="red")
ax[0].set(xlabel="Aqua weekly FRP (MW)", ylabel="VIIRS weekly FRP (MW)",
          title=f"Weekly FRP: r = {lr.rvalue:.2f}, slope = {lr.slope:.2f}")
monthly["ratio"].plot.bar(ax=ax[1], title="VIIRS / Aqua FRP ratio by month")
ax[1].set_xticklabels([d.strftime("%b") for d in monthly.index], rotation=0)
plt.tight_layout()
plt.savefig("docs/day3_relation.png", dpi=130)
print("\nsaved docs/day3_relation.png")