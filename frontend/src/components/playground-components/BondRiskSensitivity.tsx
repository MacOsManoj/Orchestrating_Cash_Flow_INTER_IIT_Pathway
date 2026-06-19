"use client";

import type React from "react";

export type CanvasComponentSize = "small" | "medium" | "large" | "full";

// New schema shape:
//
// "data": [
//   { "bond_1 name": "DV01 value" },
//   { "bond_2 name": "DV01 value" }
// ]
export type BondRiskRowRaw = {
  [bondName: string]: string | number;
};

export interface BondRiskSensitivityProps {
  data: BondRiskRowRaw[];
}

interface NormalizedBondRiskRow {
  name: string;
  dv01?: string;
}

type BondRiskSensitivityComponent = React.FC<BondRiskSensitivityProps> & {
  canvasSize?: CanvasComponentSize;
};

export const BondRiskSensitivity: BondRiskSensitivityComponent = ({ data }) => {
  // Normalize the schema into a clean list
  const rows: NormalizedBondRiskRow[] = (data || []).flatMap((item) =>
    Object.entries(item).map(([name, value]) => ({
      name,
      dv01: value != null ? String(value) : undefined,
    })),
  );

  return (
    <div className="w-full h-full p-2 sm:p-2.5 md:p-3">
      <div className="h-full w-full rounded-lg bg-[#020617] border border-slate-800 p-2 sm:p-2.5 md:p-3 flex flex-col">
        {/* Header - compact */}
        <div className="mb-2 sm:mb-2.5 md:mb-3">
          <h2 className="text-xs sm:text-sm md:text-base font-semibold text-white leading-tight">
            Bond Risk Sensitivity
          </h2>
          <p className="text-[9px] sm:text-[10px] md:text-xs text-slate-400 mt-0.5 leading-tight">
            DV01 per bond
          </p>
        </div>

        {/* Table - compact */}
        <div className="flex-1 overflow-y-auto">
          {rows.length === 0 ? (
            <p className="text-[10px] sm:text-xs text-slate-500">
              No data
            </p>
          ) : (
            <table className="w-full text-[9px] sm:text-[10px] md:text-xs border-collapse">
              <thead>
                <tr className="border-b border-slate-700/60 sticky top-0 bg-[#020617]">
                  <th className="text-left text-slate-400 font-medium py-1 sm:py-1.5 px-1 sm:px-2 md:px-3">
                    Bond
                  </th>
                  <th className="text-right text-slate-400 font-medium py-1 sm:py-1.5 px-1 sm:px-2 md:px-3">
                    DV01
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, idx) => (
                  <tr
                    key={`${row.name}-${idx}`}
                    className="border-b border-slate-800/40 last:border-b-0 hover:bg-slate-900/30 transition-colors"
                  >
                    <td className="py-1 sm:py-1.5 px-1 sm:px-2 md:px-3 text-slate-100 truncate font-medium">
                      {row.name}
                    </td>
                    <td className="py-1 sm:py-1.5 px-1 sm:px-2 md:px-3 text-right text-slate-200 tabular-nums">
                      {row.dv01 ?? "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
};

BondRiskSensitivity.canvasSize = "small";
