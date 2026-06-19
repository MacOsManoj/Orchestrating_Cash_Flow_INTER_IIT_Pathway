"use client"

import { useState } from "react"
import { DashboardCard } from "../ui/dashboard-card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts"

const curveData = {
  Forward: [
    { term: "3M", bond: 2.1, benchmark: 2.0 },
    { term: "1Y", bond: 2.3, benchmark: 2.2 },
    { term: "5Y", bond: 2.6, benchmark: 2.5 },
    { term: "10Y", bond: 2.85, benchmark: 2.75 },
    { term: "30Y", bond: 3.2, benchmark: 3.1 },
  ],
  Custom: [
    { term: "3M", bond: 2.0, benchmark: 1.95 },
    { term: "1Y", bond: 2.25, benchmark: 2.15 },
    { term: "5Y", bond: 2.7, benchmark: 2.6 },
    { term: "10Y", bond: 2.9, benchmark: 2.8 },
    { term: "30Y", bond: 3.3, benchmark: 3.2 },
  ],
}

export function YieldCurveChart() {
  const [activeCurve, setActiveCurve] = useState<keyof typeof curveData>("Forward")
  const data = curveData[activeCurve]

  return (
    <DashboardCard
      title="Yield Curve vs Benchmark"
      className="bg-[#143432]"
      headerAction={
        <div className="flex gap-2">
          {(Object.keys(curveData) as Array<keyof typeof curveData>).map((curve) => (
            <button
              key={curve}
              onClick={() => setActiveCurve(curve)}
              className={`rounded px-2 py-1 text-xs transition-colors ${
                activeCurve === curve
                  ? "bg-[#00c7a5] text-[#0b1623]"
                  : "text-[#8a99ab] hover:bg-[#2a3643] hover:text-[#e1e7ef]"
              }`}
            >
              {curve}
            </button>
          ))}
        </div>
      }
    >
      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a3643" />
            <XAxis dataKey="term" stroke="#8a99ab" style={{ fontSize: "12px" }} />
            <YAxis stroke="#8a99ab" style={{ fontSize: "12px" }} domain={[1.5, 3.5]} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#161e27",
                border: "1px solid #2a3643",
                borderRadius: "8px",
                color: "#e1e7ef",
              }}
              formatter={(value: number) => [`${value.toFixed(2)}%`, ""]}
            />
            <Legend wrapperStyle={{ color: "#8a99ab", fontSize: "12px" }} />
            <Line type="monotone" dataKey="bond" stroke="#00c7a5" strokeWidth={2} name="Bond" dot={{ r: 4 }} />
            <Line
              type="monotone"
              dataKey="benchmark"
              stroke="#8a99ab"
              strokeWidth={2}
              strokeDasharray="5 5"
              name="Benchmark"
              dot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </DashboardCard>
  )
}
