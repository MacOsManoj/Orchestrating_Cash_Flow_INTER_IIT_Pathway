"use client";

import type React from "react";

export interface CorrelationMatrixFXProps {
  labels?: string[];
  matrix: number[][];
  title?: string;
  subtitle?: string;
}

// For layout engine
export type CanvasComponentSize = "small" | "medium" | "large" | "full";

export const CorrelationMatrixFX: React.FC<CorrelationMatrixFXProps> & {
  canvasSize?: CanvasComponentSize;
} = ({
  labels,
  matrix,
  title = "Correlation (90D Rolling)",
  subtitle = "FX pairs & Commodities Cross",
}) => {
  const dimension = matrix.length;

  const effectiveLabels =
    labels && labels.length === dimension
      ? labels
      : Array.from({ length: dimension }, (_, i) => `Asset ${i + 1}`);

  const getCellColor = (value: number): string => {
    if (value === 1.0) {
      return "bg-emerald-500";
    } else if (value >= 0.7) {
      return "bg-teal-500";
    } else if (value >= 0.4) {
      return "bg-teal-600";
    } else if (value >= 0) {
      return "bg-teal-700";
    } else if (value >= -0.5) {
      return "bg-red-900/80";
    } else {
      return "bg-red-900";
    }
  };

  return (
    <div className="w-full rounded-2xl bg-gradient-to-br from-teal-950 via-slate-900 to-teal-950 px-4 py-3 md:px-5 md:py-4">
      {/* Header - compact */}
      <div className="mb-3">
        <h1 className="text-white text-base md:text-lg font-semibold leading-tight">
          {title}
        </h1>
        <p className="text-gray-400 text-xs md:text-sm mt-0.5">
          {subtitle}
        </p>
      </div>

      {/* Matrix */}
      <div className="overflow-x-auto">
        <div className="inline-block min-w-full">
          {/* Header Row */}
          <div className="flex mb-1.5">
            <div className="w-24 md:w-28" />
            {effectiveLabels.map((label, idx) => (
              <div
                key={`header-${idx}`}
                className="flex-1 min-w-[90px] md:min-w-[110px] text-center px-1.5"
              >
                <span className="text-gray-300 text-xs md:text-sm font-medium">
                  {label}
                </span>
              </div>
            ))}
          </div>

          {/* Matrix Rows */}
          {matrix.map((row, rowIdx) => (
            <div key={`row-${rowIdx}`} className="flex mb-1.5 last:mb-0">
              {/* Row Label */}
              <div className="w-24 md:w-28 flex items-center">
                <span className="text-gray-300 text-xs md:text-sm font-medium truncate">
                  {effectiveLabels[rowIdx] ?? `Asset ${rowIdx + 1}`}
                </span>
              </div>

              {/* Correlation Cells */}
              {row.map((value, colIdx) => (
                <div
                  key={`cell-${rowIdx}-${colIdx}`}
                  className="flex-1 min-w-[90px] md:min-w-[110px] px-1.5"
                >
                  <div
                    className={`${getCellColor(
                      value
                    )} rounded-lg py-2 md:py-2.5 flex items-center justify-center`}
                  >
                    <span className="text-white text-xs md:text-sm font-semibold">
                      {Number.isFinite(value) ? value.toFixed(2) : "—"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// default layout hint for your stacking engine
CorrelationMatrixFX.canvasSize = "large";
