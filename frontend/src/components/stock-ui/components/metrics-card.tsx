import { ChevronRight } from "lucide-react"
import type { MetricItem } from "../data/stock-data"

interface MetricsCardProps {
  metricsData: MetricItem[]
}

export function MetricsCard({ metricsData }: MetricsCardProps) {
  return (
    <div className="border border-teal-700/50 rounded-lg p-6 bg-[#0a2428] h-full w-full">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Metrics:</h3>
        <button className="text-white hover:text-emerald-500 transition-colors">
          <ChevronRight className="h-5 w-5" />
        </button>
      </div>
      <div className="space-y-2">
        {metricsData.map((metric, index) => (
          <div key={index} className="text-gray-400 text-sm">
            {metric.label} {metric.value && <span className="text-white">{metric.value}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}
