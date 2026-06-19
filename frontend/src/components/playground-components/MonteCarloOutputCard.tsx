import React from "react";

type MonteCarloResultValue = number | string;

interface MonteCarloOutputCardProps {
  // Support both direct results prop and nested data.results
  results?: Record<string, MonteCarloResultValue>;
  data?: {
    results: Record<string, MonteCarloResultValue>;
  };
}

// Define the fixed keys and their display configuration
interface MetricConfig {
  key: string;
  label: string;
  format: (value: MonteCarloResultValue) => string;
}
console.log("MonteCarloOutputCard loaded");
// Fixed list of metrics in display order
const METRIC_CONFIGS: MetricConfig[] = [
  {
    key: "Min Return",
    label: "Min Return",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return value.toFixed(4);
      return String(value);
    },
  },
  {
    key: "Max Return",
    label: "Max Return",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return value.toFixed(4);
      return String(value);
    },
  },
  {
    key: "Mean Return",
    label: "Mean Return",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return value.toFixed(4);
      return String(value);
    },
  },
  {
    key: "Median Return",
    label: "Median Return",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return value.toFixed(4);
      return String(value);
    },
  },
  {
    key: "Std Deviation",
    label: "Std Deviation",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return value.toFixed(4);
      return String(value);
    },
  },
  {
    key: "Probability of Loss",
    label: "Probability of Loss",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return `${(value * 100).toFixed(2)}%`;
      return String(value);
    },
  },
  {
    key: "Num Simulations",
    label: "Num Simulations",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return value.toLocaleString();
      return String(value);
    },
  },
  {
    key: "Num Days",
    label: "Num Days",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return value.toString();
      return String(value);
    },
  },
  {
    key: "Analysis Date",
    label: "Analysis Date",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "string") {
        try {
          const date = new Date(value);
          if (!isNaN(date.getTime())) {
            return date.toLocaleDateString();
          }
        } catch {
          // Fall through to string conversion
        }
      }
      return String(value);
    },
  },
  {
    key: "History Days",
    label: "History Days",
    format: (value) => {
      if (value === null || value === undefined) return "N/A";
      if (typeof value === "number") return value.toString();
      return String(value);
    },
  },
];

export const MonteCarloOutputCard: React.FC<MonteCarloOutputCardProps> & {
  canvasSize?: string;
} = ({ data, results: directResults }) => {
  // Handle both data.results and direct results prop
  // CanvasArea spreads item.data, so if data={results: {...}}, it becomes results={...}
  const results = directResults || data?.results || {};
  
  console.log("MonteCarloOutputCard rendering with props:", { data, directResults });
  console.log("MonteCarloOutputCard rendering with results:", results);
  
  const stockName = String(results["ticker"] || "Stock");

  // Map the fixed metric configs to actual values from results
  const entries = METRIC_CONFIGS.map((config) => ({
    key: config.key,
    label: config.label,
    value: results[config.key],
    formattedValue: config.format(results[config.key]),
  })).filter((entry) => entry.value !== null && entry.value !== undefined);

  if (entries.length === 0) {
    return (
      <div className="w-full bg-[#020617] border border-slate-800 rounded-xl px-3 py-3 shadow-sm">
        <h2 className="text-xs sm:text-sm font-semibold text-white mb-2 leading-tight">
          Monte Carlo Simulation — {stockName}
        </h2>
        <p className="text-slate-400 text-[10px] sm:text-xs">No simulation data available</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full bg-[#020617] border border-slate-800 rounded-xl px-3 py-3 shadow-sm flex flex-col">
      {/* Header */}
      <h2 className="text-xs sm:text-sm font-semibold text-white mb-2 leading-tight">
        Monte Carlo Simulation — {stockName}
      </h2>

      {/* Content Grid */}
      <div className="flex-1 grid grid-cols-2 gap-2 sm:gap-2.5 overflow-y-auto">
        {entries.map((entry) => (
          <div
            key={entry.key}
            className="bg-[#030712] px-2 py-2 rounded-lg border border-slate-800 flex flex-col"
          >
            <p className="text-[9px] sm:text-[10px] text-slate-400 leading-tight truncate">
              {entry.label}
            </p>
            <p className="text-[10px] sm:text-xs font-semibold text-slate-100 mt-0.5 leading-tight break-words">
              {entry.formattedValue}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

MonteCarloOutputCard.canvasSize = "medium";
