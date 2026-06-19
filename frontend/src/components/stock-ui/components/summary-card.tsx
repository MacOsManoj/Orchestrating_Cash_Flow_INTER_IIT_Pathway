import type { SummaryData } from "../data/stock-data"

interface SummaryCardProps {
  summaryData: SummaryData
}

export function SummaryCard({ summaryData }: SummaryCardProps) {
  return (
    <div className="border border-teal-700/50 rounded-lg p-6 bg-[#0a2428] flex-shrink-0">
      <h3 className="text-lg font-semibold text-white mb-4">{summaryData.title}</h3>
      {summaryData.points.map((point, index) => (
        <p key={index} className="text-gray-300 text-sm">
          {point}
        </p>
      ))}
    </div>
  )
}
