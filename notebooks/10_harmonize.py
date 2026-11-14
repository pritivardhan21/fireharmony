"""Harmonise MODIS (Aqua) and VIIRS (S-NPP) daytime vegetation-fire hotspots into a monthly
0.25-degree grid on one common 'S-NPP-equivalent' scale. Run from the project root.

Method (notebooks 07-08): S-NPP/Aqua count ratio = A * m**gap_h, where gap_h is the Aqua-minus-S-NPP
median overpass-time gap in hours (Oct-Nov, IST). Aqua counts x ratio = S-NPP-equivalent counts.
Years without S-NPP use the mean gap of the first five overlap years (flagged as assumed)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

INTERIM = Path("data/interim")
PROCESSED = Path("data/processed")
WEB = Path("web/public/data")
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = 73.8, 27.6, 77.6, 32.6
STEP = 0.25
NEED = {"latitude", "longitude", "datetime_utc", "satellite", "type", "confidence", "daynight", "frp"}


def load():
    modis = pd.read_parquet(INTERIM / "modis_all.parquet")
    viirs = pd.read_parquet(INTERIM / "viirs_all.parquet")
    for name, d in (("modis_all", modis), ("viirs_all", viirs)):
        missing = NEED - set(d.columns)
        if missing:
            raise SystemExit(f"{name}.parquet lacks {sorted(missing)}; columns are {list(d.columns)}")
    modis = modis[(modis["type"] == 0) & (pd.to_numeric(modis["confidence"], errors="coerce") >= 30)]
    viirs = viirs[(viirs["type"] == 0) & (viirs["confidence"] != "l")]
    df = pd.concat([modis, viirs], ignore_index=True)
    df = df[df["daynight"] == "D"].copy()
    ist = df["datetime_utc"].dt.tz_convert("Asia/Kolkata")
    df["year"], df["month"] = ist.dt.year, ist.dt.month
    df["hour"] = ist.dt.hour + ist.dt.minute / 60
    return df


def ratios(df):
    s = df[df["month"].isin([10, 11])]
    aq, sn = s[s["satellite"] == "Aqua"], s[s["satellite"] == "SNPP"]
    return pd.DataFrame({
        "gap_h": aq.groupby("year")["hour"].median() - sn.groupby("year")["hour"].median(),
        "count_ratio": sn.groupby("year").size() / aq.groupby("year").size(),
        "frp_ratio": sn.groupby("year")["frp"].sum() / aq.groupby("year")["frp"].sum(),
    }).dropna()


def loglin(gap, ratio):
    k, a = np.polyfit(gap, np.log(ratio), 1)
    return float(np.exp(a)), float(np.exp(k))  # ratio at zero gap, multiplier per extra hour


def main():
    df = load()
    print("detections by satellite:", df.groupby("satellite").size().to_dict())
    print("years:", int(df["year"].min()), "to", int(df["year"].max()))

    r = ratios(df)
    a_c, m_c = loglin(r["gap_h"], r["count_ratio"])
    a_f, m_f = loglin(r["gap_h"], r["frp_ratio"])
    print(f"\ncount ratio: {a_c:.2f} at zero gap, x{m_c:.2f} per hour (notebook 07: 5.35, 0.55)")
    print(f"FRP ratio:   {a_f:.2f} at zero gap, x{m_f:.2f} per hour (notebook 07: 2.19, 0.50)")
    tr = r[r.index <= 2023]
    a_t, m_t = loglin(tr["gap_h"], tr["count_ratio"])
    for y in (2024, 2025):
        if y in r.index:
            pred = a_t * m_t ** r.loc[y, "gap_h"]
            obs = r.loc[y, "count_ratio"]
            print(f"held-out {y} (fit on <= 2023): predicted {pred:.2f}, observed {obs:.2f} "
                  f"({100 * (pred / obs - 1):+.0f}%)")

    aq_years = sorted(int(y) for y in df.loc[df["satellite"] == "Aqua", "year"].unique())
    assumed_gap = float(r["gap_h"].sort_index().iloc[:5].mean())
    gap = {y: float(r["gap_h"][y]) if y in r.index else assumed_gap for y in aq_years}
    assumed = {y: bool(y not in r.index) for y in aq_years}
    factor = {y: a_c * m_c ** g for y, g in gap.items()}

    # monthly 0.25-degree grid
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
    fac = np.array([factor.get(int(y), 0.0) for y in yr])
    harm = aq * fac[:, None]

    rows = []
    for y in range(y0, y1 + 1):
        sel = yr == y
        on = sel & np.isin(mo, (10, 11))
        rows.append({
            "year": y, "aqua_raw": aq[sel].sum(), "snpp_observed": sn[sel].sum(),
            "harmonised": harm[sel].sum(), "factor": factor.get(y, np.nan),
            "gap_h": gap.get(y, np.nan), "gap_assumed": assumed.get(y, None),
            "octnov_harm_over_obs": harm[on].sum() / sn[on].sum() if sn[on].sum() else np.nan,
            "allyear_harm_over_obs": harm[sel].sum() / sn[sel].sum() if sn[sel].sum() else np.nan,
        })
    summary = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print("\n=== Harmonised (Aqua x factor) versus observed S-NPP, whole year and Oct-Nov ===")
    print(summary.round(2).to_string(index=False))

    rr, cc = np.divmod(np.arange(nc), nlon)
    out = {
        "meta": {
            "box": [LON_MIN, LAT_MIN, LON_MAX, LAT_MAX], "step": STEP, "nlat": nlat, "nlon": nlon,
            "start_year": y0, "end_year": y1, "n_months": nm,
            "filters": "vegetation fire (type 0), daytime, MODIS confidence >= 30, VIIRS confidence not low",
            "model": {"count_ratio_at_zero_gap": a_c, "count_multiplier_per_hour": m_c,
                      "frp_ratio_at_zero_gap": a_f, "frp_multiplier_per_hour": m_f},
            "gap_by_year": gap, "gap_assumed": assumed, "factor_by_year": factor,
            "validation": summary.replace({np.nan: None}).to_dict(orient="records"),
        },
        "cells": {"lat": (LAT_MIN + (rr + 0.5) * STEP).round(4).tolist(),
                  "lon": (LON_MIN + (cc + 0.5) * STEP).round(4).tolist()},
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
        "cell": ci, "lat": out["cells"]["lat"][0:0] or np.array(out["cells"]["lat"])[ci],
        "lon": np.array(out["cells"]["lon"])[ci], "year": yr[mi], "month": mo[mi],
        "aqua_raw": aq[mi, ci], "snpp_raw": sn[mi, ci], "harmonised_snpp_equiv": harm[mi, ci].round(2),
    })
    long.to_csv(PROCESSED / "harmonised_monthly_cells.csv", index=False)
    print(f"wrote {PROCESSED / 'harmonised_monthly_cells.csv'} ({len(long):,} rows)")


if __name__ == "__main__":
    main()