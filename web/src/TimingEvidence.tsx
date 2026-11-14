import { useEffect, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type Row = {
  year: number;
  snpp_day: number;
  snpp_night: number;
  aqua_day: number;
  snpp_day_hour: number | null;
  aqua_day_hour: number | null;
};

const fmt = (v: number) => Math.round(v).toLocaleString("en-IN");
const pct = (now: number, before: number) => `${now >= before ? "+" : "−"}${Math.abs(Math.round((now / before - 1) * 100))}%`;
const hhmm = (h: number) => {
  const m = Math.round(h * 60);
  return `${Math.floor(m / 60)}:${String(m % 60).padStart(2, "0")}`;
};

export default function TimingEvidence() {
  const [rows, setRows] = useState<Row[] | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    fetch("/data/timing_evidence.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Row[]>;
      })
      .then(setRows)
      .catch((e) => setErr(String(e)));
  }, []);

  const card = "rounded-lg border border-slate-200 bg-white p-4 shadow-sm";
  if (err) return <div className={card}>Timing evidence could not be loaded: {err}</div>;
  if (!rows) return <div className={card}>Loading timing evidence…</div>;

  const a = rows.find((r) => r.year === 2021);
  const z = rows[rows.length - 1];
  const counts = rows.map((r) => ({
    year: r.year,
    "S-NPP day": r.snpp_day,
    "S-NPP night": r.snpp_night,
    "Aqua day": r.aqua_day,
  }));
  const hours = rows.map((r) => ({ year: r.year, "S-NPP day pass": r.snpp_day_hour, "Aqua day pass": r.aqua_day_hour }));

  return (
    <div className={card}>
      <h2 className="font-semibold">Why recent months look low: a timing effect visible in the satellite data</h2>
      <p className="mb-3 text-xs text-slate-600">
        Oct–Nov detections for the whole study box. Polar-orbiting satellites only see a fire if it is burning when they
        pass overhead.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <h3 className="mb-1 text-sm font-medium">Detections per season (log scale)</h3>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={counts}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis scale="log" domain={[100, 200000]} ticks={[100, 1000, 10000, 100000]} allowDataOverflow />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="S-NPP day" stroke="#21908d" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="S-NPP night" stroke="#440154" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Aqua day" stroke="#d95f02" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div>
          <h3 className="mb-1 text-sm font-medium">Median daytime overpass time (IST)</h3>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={hours}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis domain={[13, 16]} tickFormatter={(v: number) => hhmm(v)} />
                <Tooltip formatter={(v) => (typeof v === "number" ? hhmm(v) : String(v))} />
                <Legend />
                <Line type="monotone" dataKey="S-NPP day pass" stroke="#21908d" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Aqua day pass" stroke="#d95f02" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {a && (
        <p className="mt-3 text-sm">
          From {a.year} to {z.year}: S-NPP daytime detections {fmt(a.snpp_day)} → {fmt(z.snpp_day)} (
          {pct(z.snpp_day, a.snpp_day)}); S-NPP night detections {fmt(a.snpp_night)} → {fmt(z.snpp_night)} (
          {pct(z.snpp_night, a.snpp_night)}); Aqua daytime detections {fmt(a.aqua_day)} → {fmt(z.aqua_day)} (
          {pct(z.aqua_day, a.aqua_day)}). Aqua's daytime pass moved from {a.aqua_day_hour ? hhmm(a.aqua_day_hour) : "?"} to{" "}
          {z.aqua_day_hour ? hhmm(z.aqua_day_hour) : "?"}; S-NPP's stayed near {z.snpp_day_hour ? hhmm(z.snpp_day_hour) : "?"}.
        </p>
      )}

      <div className="mt-3 space-y-2 text-sm text-slate-700">
        <p>
          <b>What this is consistent with.</b> Night detections are far too few to have absorbed the loss, and the
          satellite that passes later (Aqua) kept more of its detections. Together this fits burning that moved to the
          afternoon and evening, between the passes. Our data cannot prove that on its own.
        </p>
        <p>
          <b>Independent evidence.</b> Geostationary satellite studies (Meteosat SEVIRI, GEO-KOMPSAT-2A) report that peak
          fire activity moved from about 1:30 pm in 2020 to about 5 pm in 2024, and that over 90% of large fires in Punjab
          in 2024–2025 occurred after 3 pm, against about 3% in 2021 (iFOREST Stubble Burning Status Report 2025; Singh et
          al. 2025, Current Science; NASA). Official fire counts fell by more than 90% since 2021, while burnt area
          mapped from Sentinel-2 fell far less (Punjab: about 31,400 km² in 2022 to about 20,000 km² in 2025).
        </p>
        <p>
          <b>What this means for the calendar.</b> The harmonised series corrects sensor differences, not this timing
          effect. After about 2022, low daytime counts do not show how much burning happened, which is also why this tool
          does not forecast.
        </p>
      </div>
    </div>
  );
}
