"use client";

import type React from "react";
import { cn } from "@/lib/utils";

// For your layout engine
export type CanvasComponentSize = "small" | "medium" | "large" | "full";

export interface AllocationAssetClass {
  name: string;
  recommendedPercentage?: number;
  recommended_percentage?: number;
  difference?: number;
}

export interface AllocationDashboardProps {
  assetClasses?: AllocationAssetClass[];
  size?: number;
  showLabels?: boolean;
  className?: string;
}

export const AllocationDashboard: React.FC<AllocationDashboardProps> & {
  canvasSize?: CanvasComponentSize;
} = ({
  assetClasses = [],
  size = 180,
  showLabels = true,
  className,
}) => {
  // Normalize and filter valid entries
  const normalizedAssets = assetClasses
    .map((a) => {
      if (!a) return null;
      // Handle both camelCase and snake_case
      const percentage =
        a.recommendedPercentage ?? a.recommended_percentage ?? 0;
      return {
        name: a.name,
        recommendedPercentage: percentage,
        difference: a.difference ?? 0,
      };
    })
    .filter(
      (a) =>
        a &&
        typeof a.recommendedPercentage === "number" &&
        !Number.isNaN(a.recommendedPercentage) &&
        a.recommendedPercentage > 0
    ) as Array<{
    name: string;
    recommendedPercentage: number;
    difference: number;
  }>;

  const total = normalizedAssets.reduce(
    (sum, a) => sum + a.recommendedPercentage,
    0
  );

  const center = size / 2;
  const radius = size * 0.35;

  const createSlicePath = (startAngle: number, endAngle: number): string => {
    const startRad = ((startAngle - 90) * Math.PI) / 180;
    const endRad = ((endAngle - 90) * Math.PI) / 180;

    const x1 = center + radius * Math.cos(startRad);
    const y1 = center + radius * Math.sin(startRad);
    const x2 = center + radius * Math.cos(endRad);
    const y2 = center + radius * Math.sin(endRad);

    const largeArc = endAngle - startAngle > 180 ? 1 : 0;

    return `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;
  };

  const palette = [
    "#7C3AED",
    "#06B6D4",
    "#10B981",
    "#F97316",
    "#EC4899",
    "#3B82F6",
    "#22C55E",
  ];

  let currentAngle = 0;

  const slices =
    total > 0
      ? normalizedAssets.map((asset, index) => {
          const angle = (asset.recommendedPercentage / total) * 360;
          const startAngle = currentAngle;
          const endAngle = currentAngle + angle;
          currentAngle = endAngle;

          const midAngle = startAngle + angle / 2;

          return {
            path: createSlicePath(startAngle, endAngle),
            label: asset.name,
            percentage: asset.recommendedPercentage,
            difference: asset.difference,
            angle: midAngle,
            color: palette[index % palette.length],
          };
        })
      : [];

  const getLabelPosition = (angle: number) => {
    const rad = ((angle - 90) * Math.PI) / 180;
    const labelRadius = radius * 0.65;
    return {
      x: center + labelRadius * Math.cos(rad),
      y: center + labelRadius * Math.sin(rad),
    };
  };

  return (
    <div
      className={cn(
        "w-full h-full px-2 py-2 sm:px-2.5 sm:py-2.5 md:px-3 md:py-3",
        className
      )}
    >
      <div className="flex flex-col items-center h-full gap-2 sm:gap-2.5 md:gap-3">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-xs sm:text-sm md:text-base font-semibold text-slate-100 leading-tight">
            Recommended Allocation
          </h2>
          <p className="text-[9px] sm:text-[10px] md:text-xs text-slate-400 leading-tight mt-0.5">
            Asset distribution
          </p>
        </div>

        {/* Pie Chart */}
        <div
          className="relative flex-shrink-0"
          style={{
            width: `min(${size}px, 55vw)`,
            height: `min(${size}px, 55vw)`,
          }}
        >
          {slices.length === 0 ? (
            <div className="flex items-center justify-center w-full h-full text-slate-500 text-[10px] sm:text-xs">
              No allocation data
            </div>
          ) : (
            <svg
              width={size}
              height={size}
              viewBox={`0 0 ${size} ${size}`}
              className="w-full h-full"
            >
              {slices.map((slice, index) => (
                <g key={index}>
                  <path
                    d={slice.path}
                    fill={slice.color}
                    className="transition-opacity hover:opacity-80 cursor-pointer"
                  />
                  {showLabels && slice.percentage > 5 && (
                    <text
                      x={getLabelPosition(slice.angle).x}
                      y={getLabelPosition(slice.angle).y}
                      textAnchor="middle"
                      dominantBaseline="middle"
                      className="fill-white font-medium pointer-events-none"
                      style={{ fontSize: `${Math.max(8, size * 0.08)}px` }}
                    >
                      {slice.percentage.toFixed(1)}%
                    </text>
                  )}
                </g>
              ))}
            </svg>
          )}
        </div>

        {/* Legend */}
        {slices.length > 0 && (
          <div className="w-full flex flex-col gap-1 sm:gap-1.5 overflow-y-auto max-h-[90px] sm:max-h-[110px]">
            {slices.map((slice, index) => {
              const difference = slice.difference ?? 0;
              const isPositive = difference > 0;
              const isNegative = difference < 0;
              return (
                <div
                  key={index}
                  className="flex items-center gap-2 text-[10px] sm:text-xs"
                >
                  <div
                    className="h-2 w-2 sm:h-2.5 sm:w-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: slice.color }}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1 justify-between">
                      <span className="text-slate-100 font-medium truncate text-[10px] sm:text-xs">
                        {slice.label}
                      </span>
                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <span className="text-slate-400 text-[9px] sm:text-[10px]">
                          {slice.percentage.toFixed(1)}%
                        </span>
                        {typeof difference === "number" && difference !== 0 && (
                          <span
                            className={`text-[9px] sm:text-[10px] font-medium ${
                              isPositive
                                ? "text-green-400"
                                : isNegative
                                ? "text-red-400"
                                : "text-slate-400"
                            }`}
                          >
                            {isPositive ? "+" : ""}
                            {difference.toFixed(1)}%
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

AllocationDashboard.canvasSize = "small";
