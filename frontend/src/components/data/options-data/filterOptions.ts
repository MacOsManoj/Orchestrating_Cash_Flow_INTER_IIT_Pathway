export interface FilterOption {
  id: string
  label: string
  value: string
  icon?: string
}

export const expiryOptions: FilterOption[] = [
  { id: "expiry-1", label: "Expiry: 15 Mar 2024", value: "15-mar-2024", icon: "calendar" },
]

export const strikeRangeOptions: FilterOption[] = [
  { id: "strike-1", label: "Strike Range: 150-190", value: "150-190", icon: "trending-up" },
]

export const volumeOptions: FilterOption[] = [{ id: "volume-1", label: "Volume > 1K", value: "1k", icon: "activity" }]

export const typeOptions: FilterOption[] = [
  { id: "type-1", label: "Type: Calls & Puts", value: "calls-puts", icon: "layers" },
]
