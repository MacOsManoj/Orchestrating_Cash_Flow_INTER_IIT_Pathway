"use client";

import { AlertTriangle, Info } from "lucide-react";
import type React from "react";

// ---- Dynamic layout size type ----
export type CanvasComponentSize = "small" | "medium" | "large" | "full";

// ---- Types aligned with schema ----
// Schema data:
// "data": [
//   { "title": "string", "timestamp": "string", "severity": "critical" | "warning" | "info" }
// ]
export interface Alert {
  title: string;
  timestamp: string;
  severity: "critical" | "warning" | "info" | string; // allow unknown, fallback handled
  id?: string;
  icon?: "alert-triangle" | "exclamation" | "info";
}

interface AlertsInsightsProps {
  alerts?: Alert[];
}

/**
 * Supports two shapes for compatibility with your schema:
 *  1) <AlertsInsights alerts={data} />
 *  2) <AlertsInsights {...data} /> where `data` is an array (schema's `data` field)
 */
type AlertsInsightsComponent = React.FC<AlertsInsightsProps | Alert[]> & {
  canvasSize?: CanvasComponentSize;
};

export const AlertsInsights: AlertsInsightsComponent = (props) => {
  // If Canvas passes the raw array (schema `data`), props will be an array.
  // If it passes an object { alerts: [...] }, use that.
  const alerts: Alert[] = Array.isArray(props) ? props : props.alerts ?? [];

  const normalizeSeverity = (
    severity: Alert["severity"],
  ): "critical" | "warning" | "info" => {
    if (severity === "critical" || severity === "warning" || severity === "info") {
      return severity;
    }
    return "info";
  };

  const getIconBgColor = (severity: Alert["severity"]) => {
    const s = normalizeSeverity(severity);
    switch (s) {
      case "critical":
        return "bg-[#3d1f1f]";
      case "warning":
        return "bg-[#3d3a1f]";
      case "info":
      default:
        return "bg-[#1f3d3d]";
    }
  };

  const getIconColor = (severity: Alert["severity"]) => {
    const s = normalizeSeverity(severity);
    switch (s) {
      case "critical":
        return "text-[#f97373]";
      case "warning":
        return "text-[#facc15]";
      case "info":
      default:
        return "text-[#22c55e]";
    }
  };

  const getBadgeColor = (severity: Alert["severity"]) => {
    const s = normalizeSeverity(severity);
    switch (s) {
      case "critical":
        return "border-[#f97373] text-[#f97373]";
      case "warning":
        return "border-[#facc15] text-[#facc15]";
      case "info":
      default:
        return "border-[#22c55e] text-[#22c55e]";
    }
  };

  const getBadgeLabel = (severity: Alert["severity"]) => {
    const s = normalizeSeverity(severity);
    switch (s) {
      case "critical":
        return "Critical";
      case "warning":
        return "Warning";
      case "info":
      default:
        return "Info";
    }
  };

  const renderIcon = (iconType: Alert["icon"] | undefined, severity: Alert["severity"]) => {
    const iconClass = `w-4 h-4 sm:w-5 sm:h-5 ${getIconColor(severity)}`;
    const effectiveIcon = iconType ?? "alert-triangle";

    switch (effectiveIcon) {
      case "alert-triangle":
        return <AlertTriangle className={iconClass} />;
      case "exclamation":
        return (
          <span className={`text-xs sm:text-sm md:text-base font-bold ${getIconColor(severity)}`}>
            !
          </span>
        );
      case "info":
      default:
        return <Info className={iconClass} />;
    }
  };

  return (
    <div className="w-full h-full p-2 sm:p-2.5 md:p-3">
      <div className="bg-[#020617] rounded-xl border border-[#1f2937] shadow-sm h-full flex flex-col">
        {/* Header - very compact, no extra right content */}
        <div className="flex items-center justify-between mb-2 sm:mb-2.5 md:mb-3 gap-2 px-1">
          <div className="flex flex-col">
            <h1 className="text-sm sm:text-base md:text-lg font-semibold text-white leading-tight">
              Alerts &amp; Insights
            </h1>
            <p className="text-[9px] sm:text-[10px] md:text-xs text-slate-400 leading-tight mt-0.5">
              Key risk and system notifications
            </p>
          </div>
        </div>

        {/* Alerts List - compact and scrollable */}
        <div className="flex-1 overflow-y-auto space-y-1 sm:space-y-1.5 md:space-y-2 pr-1">
          {alerts.length === 0 ? (
            <p className="text-slate-500 text-[11px] sm:text-xs px-1">
              No alerts at the moment.
            </p>
          ) : (
            alerts.map((alert, index) => (
              <div
                key={alert.id ?? `alert-${index}`}
                className="flex items-center gap-2 sm:gap-3 py-1 sm:py-1.5 md:py-2 px-1 rounded-md hover:bg-[#020b16]"
              >
                {/* Icon */}
                <div
                  className={`flex items-center justify-center w-7 h-7 sm:w-8 sm:h-8 md:w-9 md:h-9 rounded-full flex-shrink-0 ${getIconBgColor(
                    alert.severity,
                  )}`}
                >
                  {renderIcon(alert.icon, alert.severity)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <h3 className="text-white text-xs sm:text-sm md:text-base font-medium leading-tight truncate">
                    {alert.title}
                  </h3>
                  <p className="text-slate-400 text-[9px] sm:text-[10px] md:text-xs leading-tight mt-0.5 truncate">
                    {alert.timestamp}
                  </p>
                </div>

                {/* Badge */}
                <div
                  className={`px-2 sm:px-2.5 py-0.5 rounded-full border text-[9px] sm:text-[10px] md:text-xs font-medium flex-shrink-0 whitespace-nowrap ${getBadgeColor(
                    alert.severity,
                  )}`}
                >
                  {getBadgeLabel(alert.severity)}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

AlertsInsights.canvasSize = "medium";
