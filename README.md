# FireHarmony

A burning-activity calendar for Punjab and Haryana (73.8–77.6°E, 27.6–32.6°N) built from NASA FIRMS MODIS and VIIRS active-fire hotspots. Built for the NASA Space Apps Challenge 2026, challenge "Harmonization of MODIS and VIIRS Hot Spots", Panaji local event.

## What it does

- Puts MODIS (Aqua) and VIIRS (S-NPP) hotspot counts on one VIIRS-equivalent scale, so the sensor of origin matters less.
- Shows a year-by-month calendar of hotspots for any area you select (drag on the grid, use presets, or type bounds), with a colour-blind-safe ramp.
- Compares the latest month with the historical median for that area.
- Downloads the monthly series for the selected area as CSV.
- Shows the evidence for why a fixed MODIS-to-VIIRS factor stops working, with validation numbers and limitations.

## Key findings (from `docs/findings.md` and `notebooks/`)

- Aqua's overpass time has drifted later relative to S-NPP: the median Oct–Nov gap grew from about 0.1–0.25 h (2012–2022) to 1.43 h in 2025.
- The S-NPP/Aqua count ratio in Oct–Nov fell from about 4.6–5.8 to 2.17 as the gap grew; a log-linear gap model predicted 2024 and 2025 within about 6% (fitted on years up to 2023).
- Outside Oct–Nov no delay effect could be detected, so the delay correction is not applied to other months.
- Per-month S-NPP/Aqua ratios calibrated on 2012–2017 predicted monthly S-NPP counts for 2018–2022 with a median absolute error of 17% (annual totals off by 8–15%, over-predicting).
- A constant monthly Aqua factor overshoots observed S-NPP by up to about 43% by 2024, which is why the harmonised series uses S-NPP where it exists (2012 onwards).
- NOAA-20 and S-NPP agree (ratio 0.98–1.05), so the decline is not a VIIRS instrument artefact. NOAA-21 FRP is 12–30% higher than S-NPP for unexplained reasons and is treated as provisional.

## Status and limitations

- **Pre-2012 bridge: loaded from MODIS Aqua 2002–2011.** Before 2012, Aqua counts are scaled by a per-calendar-month S-NPP/Aqua ratio calibrated on 2012–2017 and validated on 2018–2022 (median error 17%); it cannot be checked against VIIRS before 2012, so those years are extrapolated. The code is `notebooks/12_final_series.py`.
- Counts are daytime hotspots, not burned area. If burning has moved later in the day, away from overpass times, recent months can look lower without less burning.
- Calibration is for this region only. Orbit drift and the later timing of burning overlap in time and are not separated.
- Not for operational decisions on its own.

## Run it

Windows PowerShell for the web app, any Python 3.12 environment with pandas, numpy, pyarrow, scipy and matplotlib for the scripts.

```
python notebooks/12_final_series.py   # builds web/public/data/monthly_grid.json and data/processed/*.csv
cd web
npm install
npm run dev                           # http://localhost:5173/
```

Raw FIRMS downloads (`data/raw/`, `data/interim/`) are not in the repository. See `docs/SOURCES.md` for what was downloaded and from where.

## Repository layout

- `notebooks/01…09` exploration and analysis, `10…12` harmonisation (12 is the final version)
- `docs/findings.md` findings log, `docs/*.png` analysis figures
- `web/` React + Vite + Tailwind + Recharts app (no backend; reads `web/public/data/monthly_grid.json`)
- `data/processed/` harmonised monthly cell table (CSV)

## Team

Pritivardhan Chothe
Pradnya Taware
Suyash Mali
