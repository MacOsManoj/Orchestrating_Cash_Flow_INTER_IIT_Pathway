"use client";

import React, { useMemo } from "react";

export type CanvasComponentSize = "small" | "medium" | "large" | "full";

export interface StockCandlePoint {
  date: string;   // e.g. "2025-02-01"
  high: number;
  low: number;
  open?: number;
  close?: number;
}

export interface StockCandlestickChartProps {
  symbol: string;
  points: StockCandlePoint[];
}

// Helpers
function parseMaybeDate(value: string): Date | null {
  const d = new Date(value);
  return isNaN(d.getTime()) ? null : d;
}

function formatDateLabel(value: string): string {
  const d = parseMaybeDate(value);
  if (!d) return value;
  return d.toLocaleDateString(undefined, { month: "short", day: "2-digit" });
}

function formatPriceLabel(value: number): string {
  // Adjust decimals if you want
  return value.toFixed(2);
}

export const StockCandlestickChart: React.FC<StockCandlestickChartProps> & {
  canvasSize?: CanvasComponentSize;
} = ({ symbol, points }) => {
  const cleaned = useMemo(
    () => (points ?? []).filter((p) => typeof p.high === "number" && typeof p.low === "number"),
    [points],
  );

  const { minPrice, maxPrice } = useMemo(() => {
    if (!cleaned.length) return { minPrice: 0, maxPrice: 1 };

    let min = Number.POSITIVE_INFINITY;
    let max = Number.NEGATIVE_INFINITY;

    for (const p of cleaned) {
      min = Math.min(min, p.low, p.open ?? p.low, p.close ?? p.low);
      max = Math.max(max, p.high, p.open ?? p.high, p.close ?? p.high);
    }

    if (!isFinite(min) || !isFinite(max) || min === max) {
      // fallback
      return { minPrice: 0, maxPrice: max || 1 };
    }

    // small padding
    const padding = (max - min) * 0.05;
    return { minPrice: min - padding, maxPrice: max + padding };
  }, [cleaned]);

  if (!cleaned.length) {
    return (
      <div className="w-full rounded-3xl bg-[#020617] p-6 flex items-center justify-center">
        <p className="text-sm text-slate-400">
          No price data available for {symbol}.
        </p>
      </div>
    );
  }

  // Layout constants
  const width = 800;
  const height = 320;
  const paddingTop = 24;
  const paddingBottom = 32;
  const paddingLeft = 60;
  const paddingRight = 24;

  const plotWidth = width - paddingLeft - paddingRight;
  const plotHeight = height - paddingTop - paddingBottom;

  const n = cleaned.length;
  const stepX = n > 1 ? plotWidth / (n - 1) : 0;

  const scaleY = (price: number): number => {
    if (maxPrice === minPrice) return paddingTop + plotHeight / 2;
    const t = (price - minPrice) / (maxPrice - minPrice); // 0 → low, 1 → high
    // But SVG y grows downward, so invert
    return paddingTop + (1 - t) * plotHeight;
  };

  const yTicks = useMemo(() => {
    const ticks = 4;
    const result: number[] = [];
    for (let i = 0; i <= ticks; i++) {
      const t = i / ticks;
      const v = minPrice + t * (maxPrice - minPrice);
      result.push(v);
    }
    return result;
  }, [minPrice, maxPrice]);

  return (
    <div className="w-full rounded-3xl bg-[#020617] p-4">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-3 px-2">
        <div>
          <h2 className="text-lg md:text-xl font-semibold text-white">
            {symbol} – Daily Candlestick
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            High / low range with optional open/close for each day
          </p>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full overflow-x-auto">
        <svg
          width={width}
          height={height}
          className="min-w-full"
          role="img"
          aria-label={`${symbol} candlestick chart`}
        >
          {/* Plot background */}
          <rect
            x={paddingLeft}
            y={paddingTop}
            width={plotWidth}
            height={plotHeight}
            fill="#020617"
            stroke="#1f2933"
            strokeWidth={1}
            rx={12}
          />

          {/* Horizontal grid + Y axis labels */}
          {yTicks.map((val, idx) => {
            const y = scaleY(val);
            return (
              <g key={`ytick-${idx}`}>
                <line
                  x1={paddingLeft}
                  y1={y}
                  x2={paddingLeft + plotWidth}
                  y2={y}
                  stroke="#1f2933"
                  strokeDasharray="2 4"
                  strokeWidth={1}
                />
                <text
                  x={paddingLeft - 8}
                  y={y}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fill="#9ca3af"
                  fontSize={11}
                >
                  {formatPriceLabel(val)}
                </text>
              </g>
            );
          })}

          {/* X axis line */}
          <line
            x1={paddingLeft}
            y1={paddingTop + plotHeight}
            x2={paddingLeft + plotWidth}
            y2={paddingTop + plotHeight}
            stroke="#1f2933"
            strokeWidth={1}
          />

          {/* X axis labels (sparse for readability) */}
          {cleaned.map((p, index) => {
            const x = paddingLeft + index * stepX;
            // show every ~max(1, n/8) point label
            const modulo = Math.max(1, Math.floor(n / 8));
            if (index % modulo !== 0 && index !== n - 1) return null;

            return (
              <text
                key={`xlabel-${index}`}
                x={x}
                y={paddingTop + plotHeight + 18}
                textAnchor="middle"
                fill="#9ca3af"
                fontSize={11}
              >
                {formatDateLabel(p.date)}
              </text>
            );
          })}

          {/* Candles */}
          {cleaned.map((p, index) => {
            const x = paddingLeft + index * stepX;
            const yHigh = scaleY(p.high);
            const yLow = scaleY(p.low);

            const hasOHLC = typeof p.open === "number" && typeof p.close === "number";
            const candleColor = hasOHLC
              ? p.close! >= p.open!
                ? "#22c55e"
                : "#ef4444"
              : "#38bdf8";

            let bodyY: number;
            let bodyHeight: number;

            if (hasOHLC) {
              const yOpen = scaleY(p.open!);
              const yClose = scaleY(p.close!);
              bodyY = Math.min(yOpen, yClose);
              bodyHeight = Math.max(2, Math.abs(yOpen - yClose));
            } else {
              const mid = (p.high + p.low) / 2;
              const yMid = scaleY(mid);
              bodyY = yMid - 4;
              bodyHeight = 8;
            }

            const bodyWidth = Math.min(18, (stepX || 18) * 0.6);

            return (
              <g key={`candle-${index}`}>
                {/* Wick */}
                <line
                  x1={x}
                  y1={yHigh}
                  x2={x}
                  y2={yLow}
                  stroke={candleColor}
                  strokeWidth={2}
                  strokeLinecap="round"
                />

                {/* Body */}
                <rect
                  x={x - bodyWidth / 2}
                  y={bodyY}
                  width={bodyWidth}
                  height={bodyHeight}
                  fill={candleColor}
                  rx={3}
                />
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};

StockCandlestickChart.canvasSize = "full";
