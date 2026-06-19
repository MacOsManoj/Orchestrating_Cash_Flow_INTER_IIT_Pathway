"use client";

import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

export type CanvasComponentSize = "small" | "medium" | "large" | "full";

export interface FxPricePoint {
  date: string;   // "2025-02-01"
  value: number;  // FX rate
}

export interface FxPriceChartProps {
  currencyPair: string;       // e.g. "EUR/USD"
  points: FxPricePoint[];     // time series
}

// Helpers
function parseMaybeDate(value: string): Date | null {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatDateLabel(value: string): string {
  const d = parseMaybeDate(value);
  if (!d) return value;
  return d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
}

function formatFx(value: number): string {
  if (!Number.isFinite(value)) return "";
  return value.toFixed(4);
}

export const FxPriceChart: React.FC<FxPriceChartProps> & {
  canvasSize?: CanvasComponentSize;
} = ({ currencyPair, points }) => {
  const data = useMemo(() => {
    const safePoints = Array.isArray(points) ? points : [];

    // Filter out invalid points to avoid runtime errors
    const cleaned = safePoints.filter(
      (p) =>
        p &&
        typeof p.date === "string" &&
        p.date.trim() !== "" &&
        typeof p.value === "number" &&
        Number.isFinite(p.value),
    );

    // Never mutate original array
    return cleaned
      .slice()
      .sort((a, b) => +new Date(a.date) - +new Date(b.date));
  }, [points]);

  const { yMin, yMax } = useMemo(() => {
    if (!data.length) {
      return { yMin: 0, yMax: 1 };
    }

    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;

    for (const p of data) {
      if (Number.isFinite(p.value)) {
        if (p.value < min) min = p.value;
        if (p.value > max) max = p.value;
      }
    }

    if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
      return { yMin: 0, yMax: max || 1 };
    }

    const padding = (max - min) * 0.05;
    return { yMin: min - padding, yMax: max + padding };
  }, [data]);

  if (!data.length) {
    return (
      <div className="w-full rounded-3xl bg-[#020617] p-8 flex items-center justify-center">
        <p className="text-sm text-slate-400">
          No FX price data available for {currencyPair || "pair"}.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full rounded-3xl bg-[#020617] p-8">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-white">
          {currencyPair || "FX Pair"} – Price Over Time
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Historical FX rate for the selected currency pair.
        </p>
      </div>

      {/* Chart */}
      <div className="w-full h-[320px] md:h-[380px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 16, right: 24, left: 8, bottom: 20 }}
          >
            <CartesianGrid
              stroke="#111827"
              strokeDasharray="3 3"
              vertical={false}
            />

            <XAxis
              dataKey="date"
              tickFormatter={formatDateLabel}
              stroke="#9ca3af"
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              axisLine={{ stroke: "#111827" }}
              tickLine={false}
            />

            <YAxis
              tickFormatter={formatFx}
              stroke="#9ca3af"
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={[yMin, yMax]}
            />

            <Tooltip
              contentStyle={{
                backgroundColor: "#020617",
                border: "1px solid #1f2937",
                borderRadius: 8,
              }}
              formatter={(value, name) => {
                if (name === "value" && typeof value === "number" && Number.isFinite(value)) {
                  return [formatFx(value), "Rate"];
                }
                // If not displayable, hide content
                return ["", ""];
              }}
              labelFormatter={(label) =>
                `Date: ${formatDateLabel(label as string)}`
              }
            />

            <Line
              type="monotone"
              dataKey="value"
              stroke="#38bdf8"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5, fill: "#38bdf8" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

FxPriceChart.canvasSize = "large";
