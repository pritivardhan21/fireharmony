import MapView from "./MapView";
import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

type SeriesKey = "harmonised" | "aqua" | "snpp";

type Meta = {
  box: number[];
  step: number;
  nlat: number;
  nlon: number;
  start_year: number;
  end_year: number;
  n_months: number;
  filters: string;
  method: string;
  ratio_by_month: Record<string, number>;
  ratio_fallback_months: number[];
  source_by_month_index: string[];
  validation_monthly: { err_pct: number }[];
  validation_annual: { year: number; err_pct: number }[];
  constant_factor_check: { year: number; scaled_over_observed: number }[];
};

type Data = {
  meta: Meta;
  cells: { lat: number[]; lon: number[] };
  aqua: number[][];
  snpp: number[][];
  harmonised: number[][];
};

type Aoi = { r0: number; r1: number; c0: number; c1: number };

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const SERIES_LABEL: Record<SeriesKey, string> = {
  harmonised: "Harmonised (VIIRS-equivalent)",
  aqua: "MODIS Aqua (raw)",
  snpp: "VIIRS S-NPP (raw)",
};
// Viridis: perceptually uniform and colour-blind safe
const STOPS = ["#440154", "#472d7b", "#3b528b", "#2c728e", "#21908d", "#27ad81", "#5cc863", "#aadc32", "#fde725"];
const CELL = 22;

function rgb(h: string): [number, number, number] {
  return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
}

function ramp(t: number): string {
  const x = Math.min(1, Math.max(0, t)) * (STOPS.length - 1);
  const i = Math.floor(x);
  const f = x - i;
  const a = rgb(STOPS[i]);
  const b = rgb(STOPS[Math.min(i + 1, STOPS.length - 1)]);
  const c = a.map((v, k) => Math.round(v + (b[k] - v) * f));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

function median(a: number[]): number {
  if (!a.length) return 0;
  const s = [...a].sort((x, y) => x - y);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const fmt = (v: number) => Math.round(v).toLocaleString("en-IN");

function sumCells(a: number[][], idx: number[]): number[] {
  return a.map((row) => {
    let s = 0;
    for (const i of idx) s += row[i];
    return s;
  });
}

export default function App() {
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/data/monthly_grid.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Data>;
      })
      .then(setData)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="p-8 text-red-700">Could not load data: {error}</div>;
  if (!data) return <div className="p-8">Loading data…</div>;
  return <Dashboard data={data} />;
}

function Dashboard({ data }: { data: Data }) {
  const { meta, cells } = data;
  const { nlat, nlon, step, box } = meta;

  const [series, setSeries] = useState<SeriesKey>("harmonised");
  const [aoi, setAoi] = useState<Aoi>({ r0: 0, r1: nlat - 1, c0: 0, c1: nlon - 1 });
  const [yFrom, setYFrom] = useState(meta.start_year);
  const [yTo, setYTo] = useState(meta.end_year);
  const [drag, setDrag] = useState<{ r: number; c: number } | null>(null);

  useEffect(() => {
    const up = () => setDrag(null);
    window.addEventListener("mouseup", up);
    return () => window.removeEventListener("mouseup", up);
  }, []);

  const mIdx = (y: number, m: number) => (y - meta.start_year) * 12 + m - 1;
  const m0 = mIdx(yFrom, 1);
  const m1 = mIdx(yTo, 12);

  const years = useMemo(() => {
    const a: number[] = [];
    for (let y = meta.start_year; y <= meta.end_year; y++) a.push(y);
    return a;
  }, [meta.start_year, meta.end_year]);
  const shownYears = years.filter((y) => y >= yFrom && y <= yTo);

  const arr = data[series];
  const aoiCells = useMemo(() => {
    const out: number[] = [];
    for (let r = aoi.r0; r <= aoi.r1; r++) for (let c = aoi.c0; c <= aoi.c1; c++) out.push(r * nlon + c);
    return out;
  }, [aoi, nlon]);

  const monthly = useMemo(() => sumCells(arr, aoiCells), [arr, aoiCells]);
  const aquaM = useMemo(() => sumCells(data.aqua, aoiCells), [data.aqua, aoiCells]);
  const snppM = useMemo(() => sumCells(data.snpp, aoiCells), [data.snpp, aoiCells]);
  const harmM = useMemo(() => sumCells(data.harmonised, aoiCells), [data.harmonised, aoiCells]);
  const coverage = useMemo(() => arr.map((row) => row.reduce((s, v) => s + v, 0)), [arr]);

  const cellTotals = useMemo(() => {
    const t = new Array<number>(nlat * nlon).fill(0);
    for (let m = m0; m <= m1; m++) {
      const row = arr[m];
      for (let i = 0; i < t.length; i++) t[i] += row[i];
    }
    return t;
  }, [arr, m0, m1, nlat, nlon]);
  const cellMax = Math.max(1, ...cellTotals);

  const latMin = box[1] + aoi.r0 * step;
  const latMax = box[1] + (aoi.r1 + 1) * step;
  const lonMin = box[0] + aoi.c0 * step;
  const lonMax = box[0] + (aoi.c1 + 1) * step;

  const setLatMin = (v: number) => setAoi((a) => ({ ...a, r0: clamp(Math.round((v - box[1]) / step), 0, a.r1) }));
  const setLatMax = (v: number) =>
    setAoi((a) => ({ ...a, r1: clamp(Math.round((v - box[1]) / step) - 1, a.r0, nlat - 1) }));
  const setLonMin = (v: number) => setAoi((a) => ({ ...a, c0: clamp(Math.round((v - box[0]) / step), 0, a.c1) }));
  const setLonMax = (v: number) =>
    setAoi((a) => ({ ...a, c1: clamp(Math.round((v - box[0]) / step) - 1, a.c0, nlon - 1) }));

  const preset = (la0: number, la1: number, lo0: number, lo1: number) => {
    const r0 = clamp(Math.floor((la0 - box[1]) / step + 1e-9), 0, nlat - 1);
    const r1 = clamp(Math.ceil((la1 - box[1]) / step - 1e-9) - 1, r0, nlat - 1);
    const c0 = clamp(Math.floor((lo0 - box[0]) / step + 1e-9), 0, nlon - 1);
    const c1 = clamp(Math.ceil((lo1 - box[0]) / step - 1e-9) - 1, c0, nlon - 1);
    setAoi({ r0, r1, c0, c1 });
  };

  const startDrag = (r: number, c: number) => {
    setDrag({ r, c });
    setAoi({ r0: r, r1: r, c0: c, c1: c });
  };
  const moveDrag = (r: number, c: number) => {
    if (!drag) return;
    setAoi({ r0: Math.min(drag.r, r), r1: Math.max(drag.r, r), c0: Math.min(drag.c, c), c1: Math.max(drag.c, c) });
  };

  // Calendar
  const calMax = Math.max(1, ...shownYears.flatMap((y) => MONTHS.map((_, i) => monthly[mIdx(y, i + 1)] ?? 0)));

  // Latest month versus historical median
  const cmp = useMemo(() => {
    let last = -1;
    for (let m = m1; m >= m0; m--) {
      if (coverage[m] > 0) {
        last = m;
        break;
      }
    }
    if (last < 0) return null;
    const cal = last % 12;
    const yr = meta.start_year + Math.floor(last / 12);
    const rows = shownYears
      .filter((y) => coverage[mIdx(y, cal + 1)] > 0)
      .map((y) => ({ year: y, value: monthly[mIdx(y, cal + 1)] }));
    const prev = rows.filter((r) => r.year !== yr);
    return { cal, yr, rows, med: median(prev.map((r) => r.value)), cur: monthly[last], n: prev.length };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [coverage, monthly, m0, m1, meta.start_year, yFrom, yTo]);

  // Drift evidence: Aqua x constant monthly factor vs observed S-NPP
  const drift = shownYears
    .map((y) => {
      let a = 0, s = 0, sc = 0;
      for (let m = 1; m <= 12; m++) {
        const i = mIdx(y, m);
        a += aquaM[i];
        s += snppM[i];
        sc += aquaM[i] * (meta.ratio_by_month[String(m)] ?? 1);
      }
      return { year: y, viirs: Math.round(s), aquaScaled: Math.round(sc), aquaRaw: Math.round(a) };
    })
    .filter((d) => d.viirs > 0 || d.aquaRaw > 0);

  const monthlyErr = median(meta.validation_monthly.map((v) => Math.abs(v.err_pct)));
  const annErr = meta.validation_annual.map((v) => v.err_pct);
  const driftChk = meta.constant_factor_check.filter((d) => d.year >= 2018);

  const downloadCsv = () => {
    const lines = ["year,month,source,aqua_raw,snpp_raw,harmonised_viirs_equiv,aoi_lat_min,aoi_lat_max,aoi_lon_min,aoi_lon_max"];
    for (let m = m0; m <= m1; m++) {
      lines.push([
        meta.start_year + Math.floor(m / 12), (m % 12) + 1, meta.source_by_month_index[m],
        aquaM[m], snppM[m], harmM[m].toFixed(1),
        latMin.toFixed(2), latMax.toFixed(2), lonMin.toFixed(2), lonMax.toFixed(2),
      ].join(","));
    }
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fireharmony_${yFrom}-${yTo}_${latMin}-${latMax}N_${lonMin}-${lonMax}E.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const card = "rounded-lg border border-slate-200 bg-white p-4 shadow-sm";
  const btn = "rounded border px-2 py-1 text-sm";
  const inputCls = "w-20 rounded border border-slate-300 px-1 py-0.5 text-sm";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="bg-slate-900 text-white">
        <div className="mx-auto max-w-7xl px-4 py-5">
          <h1 className="text-2xl font-semibold">FireHarmony</h1>
          <p className="mt-1 text-sm text-slate-300">
            A consistent burning-activity calendar for the Punjab–Haryana stubble-burning region (a rectangular box, 73.8–77.6°E, 27.6–32.6°N) from MODIS and VIIRS active-fire hotspots,{" "}
            {meta.start_year}–{meta.end_year}
          </p>
          {meta.start_year >= 2012 && (
            <p className="mt-2 inline-block rounded bg-amber-200 px-2 py-1 text-xs text-amber-900">
              Pre-2012 MODIS bridge not loaded: the calendar starts in {meta.start_year}
            </p>
          )}
        </div>
      </header>

      <main className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[22rem_1fr]">
        <section className="space-y-4">
          <div className={card}>
            <h2 className="mb-2 font-semibold">Data series</h2>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(SERIES_LABEL) as SeriesKey[]).map((k) => (
                <button
                  key={k}
                  onClick={() => setSeries(k)}
                  className={`${btn} ${series === k ? "border-slate-900 bg-slate-900 text-white" : "border-slate-300 bg-white"}`}
                  aria-pressed={series === k}
                >
                  {SERIES_LABEL[k]}
                </button>
              ))}
            </div>
            <div className="mt-3 flex items-center gap-2 text-sm">
              <label>
                From{" "}
                <select
                  className={inputCls}
                  value={yFrom}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    setYFrom(v);
                    if (v > yTo) setYTo(v);
                  }}
                >
                  {years.map((y) => <option key={y}>{y}</option>)}
                </select>
              </label>
              <label>
                to{" "}
                <select
                  className={inputCls}
                  value={yTo}
                  onChange={(e) => {
                    const v = Number(e.target.value);
                    setYTo(v);
                    if (v < yFrom) setYFrom(v);
                  }}
                >
                  {years.map((y) => <option key={y}>{y}</option>)}
                </select>
              </label>
            </div>
          </div>

          <div className={card}>
            <h2 className="mb-1 font-semibold">Area of interest</h2>
            <p className="mb-2 text-xs text-slate-600">
              Drag on the grid, use a preset, or type bounds (0.25° steps). Colour shows total hotspots in the chosen
              years.
            </p>
            <div className="mb-2 flex flex-wrap gap-2">
              <button className={`${btn} border-slate-300`} onClick={() => preset(box[1], box[3], box[0], box[2])}>Whole region</button>
              <button className={`${btn} border-slate-300`} onClick={() => preset(29.5, 32.5, 73.8, 77.0)}>Punjab area (box)</button>
              <button className={`${btn} border-slate-300`} onClick={() => preset(27.6, 30.9, 74.4, 77.6)}>Haryana area (box)</button>
            </div>
            <svg
              width={nlon * CELL}
              height={nlat * CELL}
              role="img"
              aria-label="Selectable grid of the study region; north is up"
              className="select-none rounded border border-slate-300"
            >
              {Array.from({ length: nlat * nlon }, (_, i) => {
                const r = Math.floor(i / nlon);
                const c = i % nlon;
                return (
                  <rect
                    key={i}
                    x={c * CELL}
                    y={(nlat - 1 - r) * CELL}
                    width={CELL}
                    height={CELL}
                    fill={ramp(Math.sqrt(cellTotals[i] / cellMax))}
                    onMouseDown={() => startDrag(r, c)}
                    onMouseEnter={() => moveDrag(r, c)}
                    style={{ cursor: "crosshair" }}
                  >
                    <title>{`${cells.lat[i].toFixed(3)}°N, ${cells.lon[i].toFixed(3)}°E: ${fmt(cellTotals[i])} hotspots`}</title>
                  </rect>
                );
              })}
              <rect
                x={aoi.c0 * CELL}
                y={(nlat - 1 - aoi.r1) * CELL}
                width={(aoi.c1 - aoi.c0 + 1) * CELL}
                height={(aoi.r1 - aoi.r0 + 1) * CELL}
                fill="none"
                stroke="#ef4444"
                strokeWidth={2.5}
                pointerEvents="none"
              />
            </svg>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
              <label>Lat min <input type="number" step={step} className={inputCls} value={latMin} onChange={(e) => setLatMin(Number(e.target.value))} /></label>
              <label>Lat max <input type="number" step={step} className={inputCls} value={latMax} onChange={(e) => setLatMax(Number(e.target.value))} /></label>
              <label>Lon min <input type="number" step={step} className={inputCls} value={lonMin} onChange={(e) => setLonMin(Number(e.target.value))} /></label>
              <label>Lon max <input type="number" step={step} className={inputCls} value={lonMax} onChange={(e) => setLonMax(Number(e.target.value))} /></label>
            </div>
            <button onClick={downloadCsv} className="mt-3 w-full rounded bg-emerald-700 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-800">
              Download monthly CSV for this area
            </button>
          </div>
        </section>

        <section className="space-y-6">
          <MapView nlat={nlat} nlon={nlon} step={step} box={box} cellTotals={cellTotals} cellMax={cellMax} aoi={aoi} onAoi={setAoi} label={SERIES_LABEL[series]} />
          <div className={card}>
            <h2 className="font-semibold">Burning activity calendar: {SERIES_LABEL[series]}</h2>
            <p className="mb-3 text-xs text-slate-600">
              Hotspots per month in the selected area ({latMin.toFixed(2)}–{latMax.toFixed(2)}°N, {lonMin.toFixed(2)}–
              {lonMax.toFixed(2)}°E). Colour uses a square-root scale of a colour-blind-safe ramp.
            </p>
            <div className="overflow-x-auto">
              <div className="grid min-w-[40rem] gap-0.5 text-xs" style={{ gridTemplateColumns: "3rem repeat(12, minmax(2.4rem, 1fr))" }}>
                <div />
                {MONTHS.map((m) => <div key={m} className="text-center font-medium">{m}</div>)}
                {shownYears.map((y) => (
                  <div key={y} className="contents">
                    <div className="pr-1 text-right font-medium leading-8">{y}</div>
                    {MONTHS.map((mn, i) => {
                      const v = monthly[mIdx(y, i + 1)] ?? 0;
                      const t = Math.sqrt(v / calMax);
                      return (
                        <div
                          key={mn}
                          className="flex h-8 items-center justify-center rounded-sm"
                          style={{ background: ramp(t), color: t < 0.6 ? "#fff" : "#111" }}
                          title={`${mn} ${y}: ${fmt(v)} hotspots`}
                          aria-label={`${mn} ${y}: ${fmt(v)} hotspots`}
                        >
                          {v >= 1 ? fmt(v) : ""}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs">
              <span>0</span>
              <div className="h-3 w-48 rounded" style={{ background: `linear-gradient(to right, ${STOPS.join(",")})` }} />
              <span>{fmt(calMax)} (max)</span>
            </div>
          </div>

          <div className={card}>
            <h2 className="font-semibold">Latest month versus the historical median</h2>
            {cmp ? (
              <>
                <p className="mt-1 text-sm">
                  {MONTHS[cmp.cal]} {cmp.yr}: <b>{fmt(cmp.cur)}</b> hotspots against a median of <b>{fmt(cmp.med)}</b> for{" "}
                  {MONTHS[cmp.cal]} in the {cmp.n} earlier years shown
                  {cmp.med >= 20 && (
                    <>
                      {" "}— <b>{(((cmp.cur / cmp.med) - 1) * 100).toFixed(0)}%</b> {cmp.cur >= cmp.med ? "above" : "below"} median
                    </>
                  )}
                  .
                </p>
                <div className="mt-2 h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={cmp.rows}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="year" />
                      <YAxis />
                      <Tooltip />
                      <ReferenceLine y={cmp.med} stroke="#ef4444" strokeDasharray="4 4" label="median" />
                      <Bar dataKey="value" name={`${MONTHS[cmp.cal]} hotspots`} fill="#2c728e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="mt-1 text-xs text-slate-500">
                  "Latest month" is the last month with data in the file and may be incomplete. Percentages are shown only when the median is at least 20 hotspots. These are daytime detections only: if burning has shifted later in the day, away from satellite overpass times, recent months can look lower without less burning (see the findings log).
                </p>
              </>
            ) : (
              <p className="text-sm text-slate-600">No data in the selected years.</p>
            )}
          </div>

          <div className={card}>
            <h2 className="font-semibold">Why the harmonisation is needed</h2>
            <p className="mb-2 text-xs text-slate-600">
              Aqua's overpass time has drifted later than S-NPP's. A fixed Aqua-to-VIIRS factor therefore stops working
              after about 2022, so the harmonised series uses VIIRS from 2012 on.
            </p>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={drift}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="viirs" name="VIIRS S-NPP observed" stroke="#21908d" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="aquaScaled" name="Aqua × constant monthly factor" stroke="#d95f02" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="aquaRaw" name="Aqua raw" stroke="#7570b3" strokeDasharray="4 4" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="mt-1 text-xs text-slate-600">
              Whole-region ratio of scaled Aqua to observed S-NPP:{" "}
              {driftChk.map((d) => `${d.year} ${d.scaled_over_observed.toFixed(2)}`).join(" · ")}
            </p>
          </div>

          <details className={card}>
            <summary className="cursor-pointer font-semibold">Methods, validation and limitations</summary>
            <div className="mt-2 space-y-2 text-sm text-slate-700">
              <p><b>Data.</b> NASA FIRMS active-fire hotspots: MODIS Collection 6.1 (Aqua) and VIIRS S-NPP. Filters: {meta.filters}. Counts are summed on a 0.25° grid by local calendar month (IST).</p>
              <p><b>Method.</b> {meta.method}. Where S-NPP exists it is used as observed. Before that, Aqua counts are multiplied by a per-calendar-month S-NPP/Aqua ratio fitted in the orbit-stable years.</p>
              <p><b>Validation.</b> Ratios fitted on 2012–2017 predicted monthly S-NPP counts for 2018–2022 with a median absolute error of {monthlyErr.toFixed(0)}%; annual totals were off by {Math.min(...annErr).toFixed(0)}% to {Math.max(...annErr).toFixed(0)}% (over-predicting, as the Aqua delay had begun to grow).</p>
              <p><b>Limitations.</b> Count ratios are calibrated for this region only. Areas are rectangular boxes on a 0.25° grid, not state boundaries: the study box also covers parts of Pakistan, Himachal Pradesh, Rajasthan, Delhi and Uttar Pradesh. An Oct–Nov delay-based correction predicted 2024–2025 ratios within about 6% as a season, but outside that season no delay effect could be detected, so we do not apply one. Orbit drift and a later daily timing of burning overlap in time and are not separated. Counts are hotspots, not burned area. Do not use this tool alone for operational decisions.</p>
              <p><b>Sources.</b> NASA FIRMS (LANCE/EOSDIS); analysis code and findings log in the project repository.</p>
            </div>
          </details>
        </section>
      </main>
    </div>
  );
}
