"""Month-specific harmonisation of Aqua (MODIS) hotspots onto an S-NPP-equivalent scale.
Per calendar month m: S-NPP/Aqua count ratio = a_m * mult_group ** gap_h, where gap_h is the
Aqua-minus-S-NPP median overpass-time gap (IST) for that month-year. a_m is fitted per month;
the delay slope is shared within two groups (Oct-Nov, other months). Run from the project root.
Writes the same JSON/CSV as 10_harmonize.py, plus the validation tables."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

INTERIM = Path("data/interim")
PROCESSED = Path("data/processed")
WEB = Path("web/public/data")
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = 73.8, 27.6, 77.6, 32.6
STEP = 0.25
MIN_N, MIN_YEARS, HOLD = 30, 6, 2023
GROUP = {m: ("octnov" if m in (10, 11) else "other") for m in range(1, 13)}
NEED = {"latitude", "longitude", "datetime_utc", "satellite", "type", "confidence", "daynight", "frp"}


def load():
    modis = pd.read_parquet(INTERIM / "modis_all.parquet")
    viirs = pd.read_parquet(INTERIM / "viirs_all.parquet")
    for name, d in (("modis_all", modis), ("viirs_all", viirs)):
        missing = NEED - set(d.columns)
        if missing:
            raise SystemExit(f"{name}.parquet lacks {sorted(missing)}")
    modis = modis[(modis["type"] == 0) & (pd.to_numeric(modis["confidence"], errors="coerce") >= 30)]
    viirs = viirs[(viirs["type"] == 0) & (viirs["confidence"] != "l")]
    df = pd.concat([modis, viirs], ignore_index=True)
    df = df[df["daynight"] == "D"].copy()
    ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
    df["year"], df["month"] = ist.dt.year, ist.dt.month
    df["hour"] = ist.dt.hour + ist.dt.minute / 60
    return df


def month_table(df):
    g = df[df["satellite"].isin(["Aqua", "SNPP"])].groupby(["year", "month", "satellite"])
    n = g.size().unstack("satellite")
    h = g["hour"].median().unstack("satellite")
    t = pd.DataFrame({"n_aqua": n["Aqua"], "n_snpp": n["SNPP"],
                      "h_aqua": h["Aqua"], "h_snpp": h["SNPP"]}).dropna()
    t = t[(t["n_aqua"] >= MIN_N) & (t["n_snpp"] >= MIN_N)].copy()
    t["gap"] = t["h_aqua"] - t["h_snpp"]
    t["ratio"] = t["n_snpp"] / t["n_aqua"]
    return t.reset_index()


def fit_fe(t, max_year):
    s = t[t["year"] <= max_year].copy()
    s["ly"] = np.log(s["ratio"])
    s = s[s.groupby("month")["ly"].transform("size") >= MIN_YEARS].copy()
    s["grp"] = s["month"].map(GROUP)
    s["x"] = s["gap"] - s.groupby("month")["gap"].transform("mean")
    s["y"] = s["ly"] - s.groupby("month")["ly"].transform("mean")
    mult, r2 = {}, {}
    for name, g in s.groupby("grp"):
        sxx = float((g["x"] ** 2).sum())
        k = float((g["x"] * g["y"]).sum() / sxx) if sxx > 1e-9 else 0.0
        mult[name] = float(np.exp(k))
        syy = float((g["y"] ** 2).sum())
        r2[name] = 1 - float(((g["y"] - k * g["x"]) ** 2).sum()) / syy if syy > 0 else float("nan")
    a = {}
    for m, g in s.groupby("month"):
        k = np.log(mult[GROUP[int(m)]])
        a[int(m)] = float(np.exp(g["ly"].mean() - k * g["gap"].mean()))
    return mult, a, r2


def make_factors(mult, a, t, years):
    gap_ym = {(int(r.year), int(r.month)): float(r.gap) for r in t.itertuples()}
    yg = t.groupby("year")["gap"].mean().to_dict()
    pool = [a[m] for m in (10, 11) if m in a] or list(a.values())
    a_fb = float(np.mean(pool))
    fac, gaps, fb = {}, {}, {}
    for y in years:
        for m in range(1, 13):
            g = gap_ym.get((y, m))
            fb_gap = g is None
            if fb_gap:
                g = float(yg.get(y, 0.15))
            am = a.get(m)
            fb_a = am is None
            if fb_a:
                am = a_fb
            fac[(y, m)] = am * mult[GROUP[m]] ** g
            gaps[(y, m)] = g
            fb[(y, m)] = bool(fb_gap or fb_a)
    return fac, gaps, fb


def main():
    df = load()
    t = month_table(df)
    print(f"month-year cells with >= {MIN_N} detections from both sensors: {len(t)}")
    mult_all, a_all, r2_all = fit_fe(t, 9999)
    mult_h, a_h, r2_h = fit_fe(t, HOLD)

    print("\n=== Delay slope: multiplier on the S-NPP/Aqua ratio per extra hour of Aqua delay ===")
    for g in ("octnov", "other"):
        print(f"{g:7} all years: x{mult_all[g]:.2f} (within-month R2 {r2_all[g]:.2f}) | "
              f"fit <= {HOLD}: x{mult_h[g]:.2f} (R2 {r2_h[g]:.2f})")
    print("zero-gap S-NPP/Aqua ratio by calendar month (all-years fit):")
    print({m: round(v, 2) for m, v in sorted(a_all.items())})
    print(f"months without a fit (use Oct-Nov intercept, flagged): "
          f"{[m for m in range(1, 13) if m not in a_all]}")

    ho = t[t["year"] > HOLD].copy()
    ho["pred"] = [a_h[int(m)] * mult_h[GROUP[int(m)]] ** g if int(m) in a_h else np.nan
                  for m, g in zip(ho["month"], ho["gap"])]
    ho["err_pct"] = 100 * (ho["pred"] / ho["ratio"] - 1)
    pd.set_option("display.width", 200)
    print(f"\n=== Out-of-sample: fit on years <= {HOLD}, predict the S-NPP/Aqua ratio in later years ===")
    print(ho[["year", "month", "n_aqua", "n_snpp", "gap", "ratio", "pred", "err_pct"]].round(2).to_string(index=False))
    ok = ho.dropna(subset=["pred"])
    if len(ok):
        print(f"median |error| {ok['err_pct'].abs().median():.0f}%, worst {ok['err_pct'].abs().max():.0f}%, "
              f"over {len(ok)} month-years")

    years = sorted(int(y) for y in df.loc[df["satellite"] == "Aqua", "year"].unique())
    fac_all, gap_all, fb_all = make_factors(mult_all, a_all, t, years)
    fac_h, _, _ = make_factors(mult_h, a_h, t, years)

    nlat = int(np.ceil((LAT_MAX - LAT_MIN) / STEP))
    nlon = int(np.ceil((LON_MAX - LON_MIN) / STEP))
    df["row"] = np.floor((df["latitude"] - LAT_MIN) / STEP).astype(int)
    df["col"] = np.floor((df["longitude"] - LON_MIN) / STEP).astype(int)
    df = df[(df["row"] >= 0) & (df["row"] < nlat) & (df["col"] >= 0) & (df["col"] < nlon)].copy()
    df["cell"] = df["row"] * nlon + df["col"]
    y0, y1 = int(df["year"].min()), int(df["year"].max())
    nm, nc = (y1 - y0 + 1) * 12, nlat * nlon
    df["mi"] = (df["year"] - y0) * 12 + df["month"] - 1

    def grid(sat):
        g = df[df["satellite"] == sat].groupby(["mi", "cell"]).size()
        arr = np.zeros((nm, nc))
        if len(g):
            idx = g.index.to_frame(index=False)
            arr[idx["mi"].to_numpy(), idx["cell"].to_numpy()] = g.to_numpy()
        return arr

    aq, sn = grid("Aqua"), grid("SNPP")
    months = np.arange(nm)
    yr, mo = y0 + months // 12, months % 12 + 1
    f_all = np.array([fac_all.get((int(y), int(m)), 0.0) for y, m in zip(yr, mo)])
    f_h = np.array([fac_h.get((int(y), int(m)), 0.0) for y, m in zip(yr, mo)])
    fb = np.array([fb_all.get((int(y), int(m)), True) for y, m in zip(yr, mo)])
    gp = np.array([gap_all.get((int(y), int(m)), np.nan) for y, m in zip(yr, mo)])
    harm, harm_h = aq * f_all[:, None], aq * f_h[:, None]

    rows = []
    for y in range(y0, y1 + 1):
        sel = yr == y
        o = sn[sel].sum()
        rows.append({"year": y, "aqua_raw": aq[sel].sum(), "snpp_observed": o,
                     "harm_all_fit": harm[sel].sum(), "harm_fit_le_2023": harm_h[sel].sum(),
                     "ratio_all_fit": harm[sel].sum() / o, "ratio_holdout": harm_h[sel].sum() / o})
    summary = pd.DataFrame(rows)
    print("\n=== Whole-year harmonised / observed S-NPP (1.0 = perfect). holdout = fit on <= 2023 ===")
    print(summary.round(2).to_string(index=False))
    for label, ms in (("Oct-Nov", (10, 11)),
                      ("other months", tuple(m for m in range(1, 13) if m not in (10, 11)))):
        sel = (yr > HOLD) & np.isin(mo, ms)
        print(f"2024-25 {label}: observed S-NPP {sn[sel].sum():,.0f}, harmonised (fit <= {HOLD}) "
              f"{harm_h[sel].sum():,.0f}, ratio {harm_h[sel].sum() / sn[sel].sum():.2f}")

    rr, cc = np.divmod(np.arange(nc), nlon)
    lat_c = (LAT_MIN + (rr + 0.5) * STEP).round(4)
    lon_c = (LON_MIN + (cc + 0.5) * STEP).round(4)
    out = {
        "meta": {
            "box": [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX], "step": STEP, "nlat": nlat, "nlon": nlon,
            "start_year": y0, "end_year": y1, "n_months": nm,
            "filters": "vegetation fire (type 0), daytime, MODIS confidence >= 30, VIIRS confidence not low",
            "method": "month-specific zero-gap ratio, delay slope shared within Oct-Nov and other months",
            "slope_multiplier_per_hour": mult_all, "slope_multiplier_fit_le_2023": mult_h,
            "zero_gap_ratio_by_month": {str(m): v for m, v in a_all.items()},
            "factor_by_month_index": [round(float(x), 4) for x in f_all],
            "gap_by_month_index": [None if np.isnan(x) else round(float(x), 3) for x in gp],
            "fallback_by_month_index": [bool(x) for x in fb],
            "validation_yearly": summary.replace({np.nan: None}).to_dict(orient="records"),
            "validation_monthly_holdout": ho.replace({np.nan: None}).to_dict(orient="records"),
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
        "harmonised_snpp_equiv": harm[mi, ci].round(2),
    })
    long.to_csv(PROCESSED / "harmonised_monthly_cells.csv", index=False)
    print(f"wrote {PROCESSED / 'harmonised_monthly_cells.csv'} ({len(long):,} rows)")


if __name__ == "__main__":
    main()

