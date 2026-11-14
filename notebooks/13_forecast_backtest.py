"""Backtest of simple forecasts of monthly hotspot totals (whole study box, harmonised series).
Run from the project root. For each target month and year, methods see only earlier years."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

d = json.loads(Path("web/public/data/monthly_grid.json").read_text())
meta = d["meta"]
y0, y1 = meta["start_year"], meta["end_year"]
tot = np.array(d["harmonised"], dtype=float).sum(axis=1)
METHODS = ["median_prior", "last_year", "mean_last3", "trend"]


def val(y, mo):
    return tot[(y - y0) * 12 + mo - 1]


def predict(method, years, vals):
    if method == "median_prior":
        return float(np.median(vals))
    if method == "last_year":
        return float(vals[-1])
    if method == "mean_last3":
        return float(np.mean(vals[-3:]))
    k, a = np.polyfit(years, np.log(np.array(vals) + 1), 1)
    return float(np.exp(a + k * (years[-1] + 1)) - 1)


rows = []
for mo in (4, 5, 10, 11):
    for t in range(y0 + 6, y1 + 1):
        yrs = list(range(y0, t))
        vals = [val(y, mo) for y in yrs]
        actual = val(t, mo)
        q10, q90 = np.quantile(vals, [0.1, 0.9])
        for me in METHODS:
            p = predict(me, yrs, vals)
            rows.append({"month": mo, "year": t, "method": me, "actual": actual, "pred": p,
                         "ape": abs(p - actual) / max(actual, 1) * 100,
                         "inside": bool(q10 <= actual <= q90)})
r = pd.DataFrame(rows)
r["period"] = np.where(r["year"] <= 2022, "2018-2022", "2023-2025")
pd.set_option("display.width", 200)
for label, months in (("Oct-Nov (stubble season)", (10, 11)), ("Apr-May (wheat residue)", (4, 5))):
    s = r[r["month"].isin(months)]
    print(f"\n=== Mean absolute % error, {label} ===")
    print(s.pivot_table(index="method", columns="period", values="ape", aggfunc="mean").round(0).to_string())
cov = r[r["method"] == "median_prior"].groupby("period")["inside"].mean().round(2)
print("\nShare of actual values inside the 10-90% range of earlier years (nominal 0.80):")
print(cov.to_string())
s = r[(r["method"] == "median_prior") & r["month"].isin([10, 11])]
print("\nOct/Nov: actual versus median of earlier years:")
print(s.pivot_table(index="year", columns="month", values=["actual", "pred"]).round(0).to_string())
