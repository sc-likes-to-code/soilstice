"use client";
import { useMemo } from "react";
import {
  Area, Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis,
} from "recharts";
import type { TimeSeries } from "@/types/contracts";
import { convertValue, formatDate, formatNumber, monthLabel, unitLabel } from "@/lib/format";
import { usePrefs } from "@/hooks/preferences";

export interface SeriesSpec {
  series: TimeSeries;
  kind: "line" | "bar" | "area" | "scatter";
  color: string;
  /** draw series.reference as a dashed overlay */
  showReference?: boolean;
  name?: string;
  /** Connect across rows where this series has no sample (irregular revisit) — NOT for genuine missing values. */
  connect?: boolean;
}

interface Row { t: string; ts: number; [k: string]: number | string | null; }

/**
 * Time-series chart over contract TimeSeries. Null points render as gaps, never zeros (UI_ARCHITECTURE §3.3).
 * Values are converted for display only.
 */
export function TimeSeriesChart({
  specs, height = 240, x = "month", yLabel, markers, yDomain,
}: {
  specs: SeriesSpec[];
  height?: number;
  x?: "month" | "date";
  yLabel?: string;
  markers?: { t: string; label: string; color?: string }[];
  yDomain?: [number | "auto" | "dataMin" | "dataMax", number | "auto" | "dataMin" | "dataMax"];
}) {
  const { units } = usePrefs();
  const rows = useMemo(() => {
    const map = new Map<string, Row>();
    specs.forEach((s, i) => {
      const put = (t: string, key: string, v: number | null) => {
        const r = map.get(t) ?? { t, ts: Date.parse(t) };
        r[key] = convertValue(v, s.series.unit, units);
        map.set(t, r);
      };
      s.series.points.forEach((p) => put(p.t.slice(0, 10), `s${i}`, p.value));
      if (s.showReference && s.series.reference) s.series.reference.points.forEach((p) => put(p.t.slice(0, 10), `r${i}`, p.value));
    });
    return [...map.values()].sort((a, b) => a.ts - b.ts);
  }, [specs, units]);

  const unit = specs[0] ? unitLabel(specs[0].series.unit, units) : "";
  const tickFmt = (v: string | number) => (x === "month" ? monthLabel(String(v)) : formatDate(String(v)));

  const monthTicks = useMemo(() => {
    if (x !== "month" || rows.length === 0) return undefined;
    return rows
      .filter((r, i) => i === 0 || r.t.slice(5, 7) !== rows[i - 1].t.slice(5, 7))
      .map((r) => r.t);
  }, [rows, x]);

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <ComposedChart data={rows} margin={{ top: markers?.length ? 22 : 8, right: 8, bottom: 0, left: -8 }}>
          <CartesianGrid stroke="#e2d9c6" strokeDasharray="2 4" vertical={false} />
          <XAxis
            dataKey="t"
            ticks={monthTicks}
            tickFormatter={tickFmt}
            tick={{ fontSize: 11, fill: "#857d6b" }}
            axisLine={{ stroke: "#cfc3aa" }}
            tickLine={false}
            minTickGap={x === "date" ? 28 : 4}
            interval={x === "month" ? 0 : "preserveStartEnd"}
          />
          <YAxis
            tick={{ fontSize: 11, fill: "#857d6b" }} axisLine={false} tickLine={false} width={48} domain={yDomain ?? ["auto", "auto"]}
            tickFormatter={(v: number) => formatNumber(v, Math.abs(v) < 2 && v !== 0 ? 2 : 0)}
            label={yLabel ?? unit ? { value: yLabel ?? unit, angle: -90, position: "insideLeft", offset: 18, style: { fontSize: 10.5, fill: "#a59c88" } } : undefined}
          />
          <Tooltip
            cursor={{ stroke: "#a3c19f", strokeWidth: 1 }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              return (
                <div className="rounded-lg border border-forest-900/10 bg-forest-950 px-3 py-2 text-[12px] text-forest-50 shadow-[var(--shadow-lift)]">
                  <p className="mb-1 font-semibold">{x === "month" ? formatDate(String(label), "month") : formatDate(String(label), "long")}</p>
                  {payload.map((p) => {
                    const key = String(p.dataKey);
                    const idx = Number(key.slice(1));
                    const spec = specs[idx];
                    const isRef = key.startsWith("r");
                    const v = p.value as number | null;
                    return (
                      <p key={key} className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full" style={{ background: isRef ? "#a59c88" : spec?.color }} />
                        <span className="text-forest-200">{isRef ? spec?.series.reference?.label : spec?.name ?? spec?.series.label}</span>
                        <span className="ml-auto pl-3 font-semibold tabular">{v === null || v === undefined ? "missing" : `${formatNumber(v, Math.abs(v) < 2 ? 2 : 1)} ${unitLabel(spec.series.unit, units)}`}</span>
                      </p>
                    );
                  })}
                </div>
              );
            }}
          />
          {markers?.map((m) => (
            <ReferenceLine key={m.t + m.label} x={m.t} stroke={m.color ?? "#366645"} strokeDasharray="3 3" label={{ value: m.label, position: "top", fontSize: 10, fill: m.color ?? "#366645" }} />
          ))}
          {specs.map((s, i) => {
            const key = `s${i}`;
            const name = s.name ?? s.series.label;
            const nodes = [];
            if (s.kind === "bar") nodes.push(<Bar key={key} dataKey={key} name={name} fill={s.color} radius={[3, 3, 0, 0]} maxBarSize={26} isAnimationActive={false} />);
            if (s.kind === "line") nodes.push(<Line key={key} dataKey={key} name={name} stroke={s.color} strokeWidth={2} dot={s.connect ? { r: 2.5, fill: s.color, strokeWidth: 0 } : false} connectNulls={!!s.connect} type="monotone" isAnimationActive={false} />);
            if (s.kind === "area") nodes.push(<Area key={key} dataKey={key} name={name} stroke={s.color} fill={s.color} fillOpacity={0.14} strokeWidth={1.8} connectNulls={false} type="monotone" isAnimationActive={false} />);
            if (s.kind === "scatter") nodes.push(<Scatter key={key} dataKey={key} name={name} fill={s.color} isAnimationActive={false} />);
            if (s.showReference && s.series.reference)
              nodes.push(<Line key={`r${i}`} dataKey={`r${i}`} name={s.series.reference.label} stroke="#a59c88" strokeWidth={1.5} strokeDasharray="4 4" dot={false} type="monotone" isAnimationActive={false} />);
            return nodes;
          })}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function ChartLegend({ items }: { items: { label: string; color: string; dashed?: boolean }[] }) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1">
      {items.map((i) => (
        <span key={i.label} className="inline-flex items-center gap-1.5 text-[11.5px] text-ink-soft">
          <span className="inline-block h-0.5 w-4" style={{ background: i.dashed ? `repeating-linear-gradient(90deg, ${i.color} 0 4px, transparent 4px 7px)` : i.color, height: i.dashed ? 2 : 3 }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}
