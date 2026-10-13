from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

viirs = pd.read_parquet(Path("data/interim/viirs_all.parquet"))
viirs = viirs[(viirs["type"] == 0) & (viirs["confidence"] != "l")].copy()
ist = viirs["datetime_utc"].dt.tz_convert("Asia/Kolkata")
viirs["year"], viirs["month"] = ist.dt.year, ist.dt.month
s = viirs[viirs["month"].isin([10, 11])]

counts = s.groupby(["year", "daynight"]).size().unstack(fill_value=0)
frp = s.groupby(["year", "daynight"])["frp"].sum().unstack(fill_value=0)
out = pd.DataFrame({
    "day_det": counts["D"],
    "night_det": counts["N"],
    "night_over_day_det": counts["N"] / counts["D"],
    "night_over_day_frp": frp["N"] / frp["D"],
})
print(out.round(3))

out["night_over_day_det"].plot(marker="o", title="S-NPP Oct-Nov: night / day detections")
plt.tight_layout()
plt.savefig("docs/day7_night_day.png", dpi=130)
print("saved docs/day7_night_day.png")