"""Final harmonised monthly series on a VIIRS (S-NPP) equivalent scale, 0.25-degree grid.
Rule: where S-NPP exists (2012+) the harmonised value is the observed S-NPP count. Before that,
Aqua counts are scaled by a per-calendar-month ratio (S-NPP / Aqua) calibrated in the orbit-stable
years 2012-2022. Validation: calibrate on 2012-2017, predict 2018-2022. Run from the project root.
Optional: put FIRMS MODIS CSVs for 2002-2011 (same box) into data/raw/modis_pre2012/."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

INTERIM = Path("data/interim")
PROCESSED = Path("data/processed")
WEB = Path("web/public/data")
PRE = Path("data/raw/modis_pre2012")
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = 73.8, 27.6, 77.6, 32.6
STEP = 0.25
CAL_END, VAL_END, TEST_END, MIN_N = 2017, 2017, 2022, 30
NEED = {"latitude", "longitude", "datetime_utc", "satellite", "type", "confidence", "daynight", "frp"}


def keep(d, viirs):
    conf = (d["confidence"] != "l") if viirs else (pd.to_numeric(d["confidence"], errors="coerce") >= 30)
    return d[(d["type"] == 0) & conf & (d["daynight"] == "D")]


def to_local(d):
    ist = d["datetime_utc"].dt.tz_convert("Asia/Kolkata")
    d = d.copy()
    d["year"], d["month"] = ist.dt.year, ist.dt.month
    return d


def load_pre():
    files = sorted(PRE.glob("*.csv"))
    if not files:
        return None
    d = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    t = pd.to_numeric(d["acq_time"], errors="coerce").fillna(0).astype(int)
    d["datetime_utc"] = (pd.to_datetime(d["acq_date"]) + pd.to_timedelta(t // 100, unit="h")
                         + pd.to_timedelta(t % 100, unit="m")).dt.tz_localize("UTC")
    d["satellite"] = d["satellite"].astype(str).replace({"A": "Aqua", "T": "Terra"})
    return d[d["satellite"] == "Aqua"]


def calibrate(good, last_year):
    c = good[good["year"] <= last_year]
    r = c.groupby("month")["ratio"].median()
    r = r[c.groupby("month")["ratio"].size() >= 3]
    fb = float(r.median())
    return {m: float(r.get(m, fb)) for m in range(1, 13)}, [m for m in range(1, 13) if m not in r.index]


def main():
    modis = pd.read_parquet(INTERIM / "modis_all.parquet")
    viirs = pd.read_parquet(INTERIM / "viirs_all.parquet")
    for name, d in (("modis_all", modis), ("viirs_all", viirs)):
        miss = NEED - set(d.columns)
        if miss:
            raise SystemExit(f"{name}.parquet lacks {sorted(miss)}")
    df = pd.concat([keep(modis, False), keep(viirs, True)], ignore_index=True)
    df = to_local(df[df["satellite"].isin(["Aqua", "SNPP"])])

    g = df.groupby(["year", "month", "satellite"]).size().unstack("satellite").fillna(0)
    t = g.rename(columns={"Aqua": "n_aqua", "SNPP": "n_snpp"}).reset_index()
    t["ratio"] = t["n_snpp"] / t["n_aqua"].where(t["n_aqua"] > 0)
    good = t[(t["n_aqua"] >= MIN_N) & (t["n_snpp"] >= MIN_N)].copy()

    ratio_val, miss_val = calibrate(good, VAL_END)
    ratio_fin, miss_fin = calibrate(good, CAL_END)
    print("calibration ratio S-NPP/Aqua by calendar month (fit 2012-2017):")
    print({m: round(v, 2) for m, v in ratio_fin.items()}, "| months using the fallback:", miss_fin)

    v = good[(good["year"] > VAL_END) & (good["year"] <= TEST_END)].copy()
    v["pred"] = v["n_aqua"] * v["month"].map(ratio_val)
    v["err_pct"] = 100 * (v["pred"] / v["n_snpp"] - 1)
    pd.set_option("display.width", 200)
    print(f"\n=== Validation: calibrate 2012-{VAL_END}, predict S-NPP counts for 2018-{TEST_END} ===")
    print(f"month-years tested: {len(v)}; median |error| {v['err_pct'].abs().median():.0f}%, "
          f"90th percentile {v['err_pct'].abs().quantile(0.9):.0f}%")
    dense = v[v["n_snpp"] >= 500]
    print(f"months with >= 500 S-NPP detections: {len(dense)}; median |error| "
          f"{dense['err_pct'].abs().median():.0f}%, worst {dense['err_pct'].abs().max():.0f}%")
    tv = t[(t["year"] > VAL_END) & (t["year"] <= TEST_END)].copy()
    tv["pred"] = tv["n_aqua"] * tv["month"].map(ratio_val)
    ann = tv.groupby("year")[["n_snpp", "pred"]].sum()
    ann["err_pct"] = 100 * (ann["pred"] / ann["n_snpp"] - 1)
    print("annual totals, predicted from Aqua vs observed S-NPP:")
    print(ann.round(0).assign(err_pct=ann["err_pct"].round(1)).to_string())

    tt = t.copy()
    tt["scaled"] = tt["n_aqua"] * tt["month"].map(ratio_fin)
    yy = tt.groupby("year")[["n_snpp", "scaled"]].sum()
    yy["scaled_over_observed"] = yy["scaled"] / yy["n_snpp"]
    print("\n=== Aqua scaled by a CONSTANT monthly factor / observed S-NPP, by year (drift evidence) ===")
    print(yy.round(2).to_string())

    cols = ["latitude", "longitude", "satellite", "year", "month"]
    dfall = df[cols]
    pre = load_pre()
    if pre is not None:
        pre = keep(pre, False)
        pre = to_local(pre)
        pre = pre[pre["year"] < 2012]
        print(f"\npre-2012 Aqua daytime vegetation-fire detections: {len(pre):,} "
              f"({int(pre['year'].min())}-{int(pre['year'].max())})" if len(pre) else "\npre-2012 files found but empty")
        dfall = pd.concat([dfall, pre[cols]], ignore_index=True)
    else:
        print("\nno pre-2012 files in data/raw/modis_pre2012: calendar starts in 2012")

    nlat = int(np.ceil((LAT_MAX - LAT_MIN) / STEP))
    nlon = int(np.ceil((LON_MAX - LON_MIN) / STEP))
    dfall = dfall.copy()
    dfall["row"] = np.floor((dfall["latitude"] - LAT_MIN) / STEP).astype(int)
    dfall["col"] = np.floor((dfall["longitude"] - LON_MIN) / STEP).astype(int)
    dfall = dfall[(dfall["row"] >= 0) & (dfall["row"] < nlat) & (dfall["col"] >= 0) & (dfall["col"] < nlon)]
    dfall["cell"] = dfall["row"] * nlon + dfall["col"]
    y0, y1 = int(dfall["year"].min()), int(dfall["year"].max())
    nm, nc = (y1 - y0 + 1) * 12, nlat * nlon
    dfall["mi"] = (dfall["year"] - y0) * 12 + dfall["month"] - 1

    def grid(sat):
        gg = dfall[dfall["satellite"] == sat].groupby(["mi", "cell"]).size()
        arr = np.zeros((nm, nc))
        if len(gg):
            idx = gg.index.to_frame(index=False)
            arr[idx["mi"].to_numpy(), idx["cell"].to_numpy()] = gg.to_numpy()
        return arr

    aq, sn = grid("Aqua"), grid("SNPP")
    months = np.arange(nm)
    yr, mo = y0 + months // 12, months % 12 + 1
    harm = np.zeros((nm, nc))
    source = []
    for i in range(nm):
        if yr[i] >= 2012:
            harm[i] = sn[i]
            source.append("viirs_observed")
        elif aq[i].sum() > 0:
            harm[i] = aq[i] * ratio_fin[int(mo[i])]
            source.append("aqua_scaled")
        else:
            source.append("no_data")
    per_year = pd.DataFrame({"year": yr, "aqua_raw": aq.sum(axis=1), "snpp_raw": sn.sum(axis=1),
                             "harmonised": harm.sum(axis=1)}).groupby("year").sum().round(0)
    print("\n=== Yearly totals over the box ===")
    print(per_year.to_string())

    rr, cc = np.divmod(np.arange(nc), nlon)
    lat_c = (LAT_MIN + (rr + 0.5) * STEP).round(4)
    lon_c = (LON_MIN + (cc + 0.5) * STEP).round(4)
    out = {
        "meta": {
            "box": [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX], "step": STEP, "nlat": nlat, "nlon": nlon,
            "start_year": y0, "end_year": y1, "n_months": nm,
            "filters": "vegetation fire (type 0), daytime, MODIS confidence >= 30, VIIRS confidence not low",
            "method": "S-NPP observed from 2012; before 2012 Aqua x monthly ratio calibrated on 2012-2017",
            "ratio_by_month": {str(k): round(x, 3) for k, x in ratio_fin.items()},
            "ratio_fallback_months": miss_fin,
            "source_by_month_index": source,
            "validation_monthly": v.round(2).to_dict(orient="records"),
            "validation_annual": ann.reset_index().round(2).to_dict(orient="records"),
            "constant_factor_check": yy.reset_index().round(3).to_dict(orient="records"),
        },
        "cells": {"lat": lat_c.tolist(), "lon": lon_c.tolist()},
        "aqua": aq.astype(int).tolist(), "snpp": sn.astype(int).tolist(),
        "harmonised": np.round(harm, 1).tolist(),
    }
    WEB.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    path = WEB / "monthly_grid.json"
    path.write_text(json.dumps(out, separators=(",", ":"), default=float))
    print(f"\nwrote {path} ({path.stat().st_size / 1e6:.2f} MB)")

    mi, ci = np.nonzero((aq > 0) | (sn > 0))
    long = pd.DataFrame({
        "cell": ci, "lat": lat_c[ci], "lon": lon_c[ci], "year": yr[mi], "month": mo[mi],
        "aqua_raw": aq[mi, ci].astype(int), "snpp_raw": sn[mi, ci].astype(int),
        "harmonised_viirs_equiv": harm[mi, ci].round(2), "source": np.array(source)[mi],
    })
    long.to_csv(PROCESSED / "harmonised_monthly_cells.csv", index=False)
    print(f"wrote {PROCESSED / 'harmonised_monthly_cells.csv'} ({len(long):,} rows)")


if __name__ == "__main__":
    main()
