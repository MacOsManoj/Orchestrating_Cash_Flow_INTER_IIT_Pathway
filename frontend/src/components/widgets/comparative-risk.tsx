"use client"

import { useState } from "react"
import { DashboardCard } from "../ui/dashboard-card"

export function ComparativeRisk() {
  const [selectedScenario, setSelectedScenario] = useState<"base" | "stress" | "favorable">("base")

  const scenarios = {
    base: { label: "Base Case", spread: "+24%", color: "#00c7a5" },
    stress: { label: "Stress (+200bps)", spread: "-15%", color: "#e24c4c" },
    favorable: { label: "Favorable (-100bps)", spread: "+45%", color: "#00c7a5" },
  }

  return (
    <DashboardCard title="Comparative & Risk Analysis" className="bg-[#143432]">
      <div className="h-full space-y-4">
        <div className="flex gap-2">
          {(Object.keys(scenarios) as Array<keyof typeof scenarios>).map((scenario) => (
            <button
              key={scenario}
              onClick={() => setSelectedScenario(scenario)}
              className={`rounded px-2 py-1 text-xs transition-colors ${
                selectedScenario === scenario
                  ? "bg-[#00c7a5] text-[#0b1623]"
                  : "text-[#8a99ab] hover:bg-[#2a3643] hover:text-[#e1e7ef]"
              }`}
            >
              {scenarios[scenario].label}
            </button>
          ))}
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="text-[#8a99ab]">Spread Trend vs UST 2045</span>
            <span style={{ color: scenarios[selectedScenario].color }}>{scenarios[selectedScenario].spread}</span>
          </div>
          <div className="flex h-12 items-center gap-1">
            <div
              className="h-full w-[25%] bg-[#8a99ab] transition-all hover:opacity-80 cursor-pointer"
              title="-100bps scenario"
            />
            <div
              className="h-full w-[35%] transition-all hover:opacity-80 cursor-pointer"
              style={{ backgroundColor: scenarios[selectedScenario].color }}
              title="Current spread"
            />
            <div
              className="h-full w-[40%] bg-[#8a99ab] transition-all hover:opacity-80 cursor-pointer"
              title="+200bps scenario"
            />
          </div>
          <div className="mt-1 flex justify-between text-xs text-[#8a99ab]">
            <span>-100bps</span>
            <span>+100bps</span>
            <span>+200bps</span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between border-b border-[#2a3643] pb-2 hover:bg-[#1a2530] px-2 py-1 rounded transition-colors cursor-pointer">
            <span className="text-xs text-[#8a99ab]">Alternative Benchmarks vs Bond 2045</span>
            <span className="text-xs font-semibold text-[#e1e7ef]">165 bps</span>
          </div>
          <div className="flex items-center justify-between border-b border-[#2a3643] pb-2 hover:bg-[#1a2530] px-2 py-1 rounded transition-colors cursor-pointer">
            <span className="text-xs text-[#8a99ab]">vs US GE 2046</span>
            <span className="text-xs font-semibold text-[#e1e7ef]">70 bps</span>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between hover:bg-[#1a2530] px-2 py-1 rounded transition-colors">
            <span className="text-xs text-[#8a99ab]">Predicted Cash Flow Stress (+100bps)</span>
            <span className="text-xs font-semibold text-[#e1e7ef]">$12.50</span>
          </div>
          <div className="flex items-center justify-between hover:bg-[#1a2530] px-2 py-1 rounded transition-colors">
            <span className="text-xs text-[#8a99ab]">2024-11-15 Coupon</span>
            <span className="text-xs font-semibold text-[#e1e7ef]">$12.50</span>
          </div>
          <div className="flex items-center justify-between hover:bg-[#1a2530] px-2 py-1 rounded transition-colors">
            <span className="text-xs text-[#8a99ab]">2025-05-15 Coupon</span>
            <span className="text-xs font-semibold text-[#e1e7ef]">$12.50</span>
          </div>
          <div className="flex items-center justify-between hover:bg-[#1a2530] px-2 py-1 rounded transition-colors">
            <span className="text-xs text-[#8a99ab]">2045-05-15 Maturity</span>
            <span className="text-xs font-semibold text-[#00c7a5]">$1,012.50</span>
          </div>
        </div>
      </div>
    </DashboardCard>
  )
}
