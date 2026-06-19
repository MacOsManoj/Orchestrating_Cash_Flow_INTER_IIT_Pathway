"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Calendar, TrendingUp, Activity, Layers } from "lucide-react"
import { expiryOptions, strikeRangeOptions, volumeOptions, typeOptions } from "../data/options-data/filterOptions"

interface FilterButtonProps {
  icon: React.ReactNode
  label: string
}

function FilterButton({ icon, label }: FilterButtonProps) {
  return (
    <Button variant="outline" className="bg-teal-700/30 border-teal-600/50 text-teal-200 hover:bg-teal-700/50 text-sm">
      {icon}
      <span className="ml-2">{label}</span>
    </Button>
  )
}

export function OptionsChainFilters() {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-sm text-teal-400/80 mr-2">Filters:</span>

      <FilterButton icon={<Calendar className="h-4 w-4" />} label={expiryOptions[0].label} />

      <FilterButton icon={<TrendingUp className="h-4 w-4" />} label={strikeRangeOptions[0].label} />

      <FilterButton icon={<Activity className="h-4 w-4" />} label={volumeOptions[0].label} />

      <FilterButton icon={<Layers className="h-4 w-4" />} label={typeOptions[0].label} />
    </div>
  )
}
