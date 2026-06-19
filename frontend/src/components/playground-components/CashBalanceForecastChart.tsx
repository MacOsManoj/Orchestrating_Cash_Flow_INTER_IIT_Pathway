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

export interface CashBalanceDataPoint {
  day: number;   // 0–30
  amount: number;
  date?: string; // will come from backend but empty / unused
}

export interface CashBalanceForecastChartProps {
  points: CashBalanceDataPoint[];
}

function formatAmount(value: number): string {
  if (!Number.isFinite(value)) return "";
  return `${(value / 1_000_000).toFixed(0)}M`;
}

export const CashBalanceForecastChart: React.FC<CashBalanceForecastChartProps> & {
  canvasSize?: CanvasComponentSize;
} = ({ points }) => {
  const sortedData = useMemo(() => {
    const safePoints = Array.isArray(points) ? points : [];

    // Filter out any invalid points to avoid NaN / undefined issues
    const cleaned = safePoints.filter(
      (p) =>
        p &&
        typeof p.day === "number" &&
        Number.isFinite(p.day) &&
        typeof p.amount === "number" &&
        Number.isFinite(p.amount),
    );

    // Never mutate original array
    return cleaned.slice().sort((a, b) => a.day - b.day);
  }, [points]);

  const { yAxisMax, ticks } = useMemo(() => {
    if (!sortedData.length) {
      return {
        yAxisMax: 1_000_000,
        ticks: [0, 250_000, 500_000, 750_000, 1_000_000],
      };
    }

    const maxAmount = Math.max(...sortedData.map((p) => p.amount));
    if (!Number.isFinite(maxAmount) || maxAmount <= 0) {
      return {
        yAxisMax: 1_000_000,
        ticks: [0, 250_000, 500_000, 750_000, 1_000_000],
      };
    }

    const maxMillions = Math.ceil(maxAmount / 1_000_000);
    const stepMillions = Math.max(1, Math.ceil(maxMillions / 4));
    const topMillions = stepMillions * 4;

    const ticksArr: number[] = [];
    for (let i = 0; i <= 4; i++) {
      ticksArr.push(i * stepMillions * 1_000_000);
    }

    return { yAxisMax: topMillions * 1_000_000, ticks: ticksArr };
  }, [sortedData]);

  if (!sortedData.length) {
    return (
      <div className="w-full rounded-3xl bg-[#0a2a2a] p-8 flex items-center justify-center">
        <p className="text-sm text-slate-400">
          No cash balance data available.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full rounded-3xl bg-[#0a2a2a] p-8">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-white">
          Cash Balance Forecast (30D)
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Projected cash balances over the next 30 days.
        </p>
      </div>

      {/* Chart */}
      <div className="w-full h-[360px] md:h-[400px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={sortedData}
            margin={{ top: 20, right: 30, left: 10, bottom: 20 }}
          >
            <CartesianGrid strokeDasharray="0" stroke="#0f2323" vertical={false} />

            {/* X axis strictly vs day */}
            <XAxis
              dataKey="day"
              tickFormatter={(day: number) => `Day ${day}`}
              stroke="#a8a8a8"
              tick={{ fill: "#a8a8a8", fontSize: 12 }}
              axisLine={{ stroke: "#0f2323" }}
              tickLine={false}
            />

            {/* Y axis with safe, dynamic ticks */}
            <YAxis
              tickFormatter={formatAmount}
              stroke="#a8a8a8"
              tick={{ fill: "#a8a8a8", fontSize: 12 }}
              axisLine={false}
              tickLine={false}
              domain={[0, yAxisMax]}
              ticks={ticks}
              label={{
                value: "Amount",
                angle: -90,
                position: "insideLeft",
                style: { fill: "#a8a8a8", fontSize: 12 },
              }}
            />

            {/* Tooltip: only shows properly formatted values */}
            <Tooltip
              isAnimationActive
              contentStyle={{
                backgroundColor: "#020617",
                border: "1px solid #1f2937",
                borderRadius: 8,
              }}
              formatter={(value, name) => {
                if (name === "amount" && typeof value === "number" && Number.isFinite(value)) {
                  return [formatAmount(value), "Amount"];
                }
                return ["", ""];
              }}
              labelFormatter={(label) => `Day ${label}`}
            />

            <Line
              type="monotone"
              dataKey="amount"
              stroke="#11d493"
              strokeWidth={3}
              dot={false}
              activeDot={{ r: 6, fill: "#11d493" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

CashBalanceForecastChart.canvasSize = "full";
