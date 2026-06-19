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
import type { CanvasComponentSize } from "./BondYieldTimeChart";

export interface BondPricePoint {
  date: string;
  price: number;
}

export interface BondPriceTimeChartProps {
  bondName: string;
  points: BondPricePoint[];
}

function formatPrice(value: number): string {
  if (!Number.isFinite(value)) return "";
  return value.toFixed(2);
}

function formatDate(label: string): string {
  const d = new Date(label);
  if (Number.isNaN(d.getTime())) return label;
  return d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
}

export const BondPriceTimeChart: React.FC<BondPriceTimeChartProps> & {
  canvasSize?: CanvasComponentSize;
} = ({ bondName, points }) => {
  const data = useMemo(() => {
    if (!Array.isArray(points)) return [];

    // Filter out bad rows + avoid mutating props
    const cleaned = points.filter(
      (p) =>
        p &&
        typeof p.date === "string" &&
        typeof p.price === "number" &&
        Number.isFinite(p.price),
    );

    const sorted = cleaned.slice().sort(
      (a, b) => +new Date(a.date) - +new Date(b.date),
    );

    // index-based x-axis (as per description)
    return sorted.map((p, idx) => ({
      ...p,
      index: idx + 1,
    }));
  }, [points]);

  if (!data.length) {
    return (
      <div className="w-full rounded-lg bg-[#020617] p-2 sm:p-2.5 md:p-3 flex items-center justify-center min-h-[200px]">
        <p className="text-[10px] sm:text-xs text-slate-400">
          No price data for {bondName}
        </p>
      </div>
    );
  }

  return (
    <div className="w-full rounded-lg bg-[#020617] p-2 sm:p-2.5 md:p-3 flex flex-col">
      {/* Header - compact */}
      <div className="flex items-baseline justify-between mb-2 sm:mb-2.5 md:mb-3 gap-2">
        <div className="min-w-0">
          <h2 className="text-xs sm:text-sm md:text-base font-semibold text-white truncate">
            {bondName} – Price
          </h2>
          <p className="text-[9px] sm:text-[10px] md:text-xs text-slate-400 mt-0.5 leading-tight">
            Period: 1Y
          </p>
        </div>
      </div>

      {/* Chart - responsive height */}
      <div className="w-full flex-1 min-h-[200px] sm:min-h-[240px] md:min-h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 4, right: 12, left: -20, bottom: 12 }}
          >
            <CartesianGrid
              stroke="#111827"
              strokeDasharray="3 3"
              vertical={false}
              strokeWidth={0.5}
            />
            <XAxis
              dataKey="index"
              stroke="#6b7280"
              tick={{ fill: "#6b7280", fontSize: 9 }}
              axisLine={{ stroke: "#1f2937", strokeWidth: 0.5 }}
              tickLine={false}
              label={{
                value: "Obs",
                position: "insideBottomRight",
                offset: -6,
                fill: "#6b7280",
                fontSize: 9,
              }}
            />
            <YAxis
              tickFormatter={formatPrice}
              stroke="#6b7280"
              tick={{ fill: "#6b7280", fontSize: 9 }}
              axisLine={false}
              tickLine={false}
              width={30}
              label={{
                value: "$",
                angle: -90,
                position: "insideLeft",
                fill: "#6b7280",
                fontSize: 9,
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#020617",
                border: "1px solid #1f2937",
                borderRadius: 6,
                padding: "6px 8px",
                fontSize: 11,
              }}
              formatter={(value, name) => {
                if (name === "price" && typeof value === "number") {
                  return [`$${formatPrice(value)}`, "Price"];
                }
                return [String(value ?? ""), name];
              }}
              labelFormatter={(_, payload) => {
                const first = payload?.[0]?.payload as
                  | (BondPricePoint & { index: number })
                  | undefined;
                return first ? formatDate(first.date) : "";
              }}
              cursor={{ stroke: "#38bdf8", strokeWidth: 1 }}
            />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#38bdf8"
              strokeWidth={1.5}
              dot={false}
              activeDot={{ r: 4, fill: "#38bdf8" }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

BondPriceTimeChart.canvasSize = "full";
