// comp-21 schema:
//
// {
//   "type": "RateVsYieldChart",
//   "data": {
//     "curveName": "Credit Spread Curve",
//     "points": [
//       {
//         "rate": "number (x-axis, e.g. coupon or risk-free rate)",
//         "yield": "number (y-axis, yield in %)"
//       }
//     ]
//   }
// }

"use client";

import React, { useMemo } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { CanvasComponentSize } from "./BondYieldTimeChart";

export interface RateYieldPoint {
  rate: number;
  yield: number;
}

export interface RateVsYieldChartProps {
  curveName: string;
  points: RateYieldPoint[];
}

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return "";
  return `${value.toFixed(2)}%`;
}

export const RateVsYieldChart: React.FC<RateVsYieldChartProps> & {
  canvasSize?: CanvasComponentSize;
} = ({ curveName, points }) => {
  const data = useMemo(() => {
    if (!Array.isArray(points)) return [];

    // Filter out invalid rows so Recharts always gets clean numeric data
    return points.filter(
      (p) =>
        p &&
        typeof p.rate === "number" &&
        Number.isFinite(p.rate) &&
        typeof p.yield === "number" &&
        Number.isFinite(p.yield),
    );
  }, [points]);

  const { xMin, xMax, yMin, yMax } = useMemo(() => {
    if (!data.length) {
      return { xMin: 0, xMax: 1, yMin: 0, yMax: 1 };
    }

    let minRate = Number.POSITIVE_INFINITY;
    let maxRate = Number.NEGATIVE_INFINITY;
    let minYield = Number.POSITIVE_INFINITY;
    let maxYield = Number.NEGATIVE_INFINITY;

    for (const p of data) {
      if (Number.isFinite(p.rate)) {
        if (p.rate < minRate) minRate = p.rate;
        if (p.rate > maxRate) maxRate = p.rate;
      }
      if (Number.isFinite(p.yield)) {
        if (p.yield < minYield) minYield = p.yield;
        if (p.yield > maxYield) maxYield = p.yield;
      }
    }

    if (!Number.isFinite(minRate) || !Number.isFinite(maxRate) || minRate === maxRate) {
      minRate = 0;
      maxRate = maxRate || 1;
    }
    if (!Number.isFinite(minYield) || !Number.isFinite(maxYield) || minYield === maxYield) {
      minYield = 0;
      maxYield = maxYield || 1;
    }

    const padX = (maxRate - minRate) * 0.05;
    const padY = (maxYield - minYield) * 0.05;

    return {
      xMin: minRate - padX,
      xMax: maxRate + padX,
      yMin: minYield - padY,
      yMax: maxYield + padY,
    };
  }, [data]);

  if (!data.length) {
    return (
      <div className="w-full rounded-3xl bg-[#020617] p-6 flex items-center justify-center">
        <p className="text-sm text-slate-400">
          No rate vs yield data available for {curveName || "curve"}.
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
            {curveName || "Rate vs Yield"} – Rate vs Yield
          </h2>
          <p className="text-xs text-slate-400 mt-1">Period: 1Y</p>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full h-72">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 24, left: 0, bottom: 16 }}>
            <CartesianGrid stroke="#111827" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="rate"
              name="Rate"
              domain={[xMin, xMax]}
              stroke="#9ca3af"
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              axisLine={{ stroke: "#111827" }}
              tickLine={false}
            />
            <YAxis
              type="number"
              dataKey="yield"
              name="Yield"
              domain={[yMin, yMax]}
              tickFormatter={formatPercent}
              stroke="#9ca3af"
              tick={{ fill: "#9ca3af", fontSize: 11 }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              cursor={{ strokeDasharray: "3 3", stroke: "#374151" }}
              contentStyle={{
                backgroundColor: "#020617",
                border: "1px solid #1f2937",
                borderRadius: 8,
              }}
              formatter={(value, name) => {
                if (name === "yield" && typeof value === "number" && Number.isFinite(value)) {
                  return [formatPercent(value), "Yield"];
                }
                if (name === "rate" && typeof value === "number" && Number.isFinite(value)) {
                  return [value.toFixed(2), "Rate"];
                }
                // hide weird stuff
                return ["", ""];
              }}
            />
            <Scatter data={data} fill="#38bdf8" line lineType="joint" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

RateVsYieldChart.canvasSize = "large";
