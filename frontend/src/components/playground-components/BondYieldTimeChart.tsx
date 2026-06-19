"use client";

import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export type CanvasComponentSize = "small" | "medium" | "large" | "full";

export interface BondYieldPoint {
  date: string; // ISO or any parsable date
  yield: number;
}

export interface BondYieldTimeChartProps {
  bondName: string;
  points: BondYieldPoint[];
}

function formatDateLabel(value: string): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
}

function formatYield(value: number): string {
  if (!Number.isFinite(value)) return "";
  return `${value.toFixed(2)}%`;
}

export const BondYieldTimeChart: React.FC<BondYieldTimeChartProps> & {
  canvasSize?: CanvasComponentSize;
} = ({ bondName, points }) => {
  const data = useMemo(() => {
    if (!Array.isArray(points)) return [];

    // Filter out invalid points first
    const cleaned = points.filter(
      (p) =>
        p &&
        typeof p.date === "string" &&
        p.date.trim() !== "" &&
        typeof p.yield === "number" &&
        Number.isFinite(p.yield),
    );

    // Clone before sort → avoid mutating read-only arrays
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
      if (Number.isFinite(p.yield)) {
        if (p.yield < min) min = p.yield;
        if (p.yield > max) max = p.yield;
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
      <div className="w-full rounded-3xl bg-[#020617] p-6 flex items-center justify-center">
        <p className="text-sm text-slate-400">
          No yield data available for {bondName || "bond"}.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full rounded-3xl bg-[#020617] p-6">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-4">
        <div>
          <h2 className="text-lg md:text-xl font-semibold text-white">
            {bondName || "Bond"} – Yield vs Time
          </h2>
          <p className="text-xs text-slate-400 mt-1">Period: 1Y</p>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 10, right: 24, left: 0, bottom: 16 }}
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
              tickFormatter={formatYield}
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
                if (name === "yield" && typeof value === "number" && Number.isFinite(value)) {
                  return [formatYield(value), "Yield"];
                }
                // Hide weird values
                return ["", ""];
              }}
              labelFormatter={(label) =>
                `Date: ${formatDateLabel(label as string)}`
              }
            />
            <Line
              type="monotone"
              dataKey="yield"
              stroke="#22c55e"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 5, fill: "#22c55e" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

BondYieldTimeChart.canvasSize = "large";
