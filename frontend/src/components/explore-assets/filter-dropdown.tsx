"use client"

import { useState, useRef, useEffect } from "react"
import { ChevronDown, Check } from "lucide-react"
import type { FilterOption } from "../explore-assets/data/types"

interface FilterDropdownProps {
  label: string
  options: FilterOption[]
  value: string
  onChange: (value: string) => void
}

export function FilterDropdown({ label, options, value, onChange }: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const selectedOption = options.find((opt) => opt.value === value)
  const displayLabel = selectedOption?.label || label

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div className="dark relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`
          flex items-center gap-2 bg-[#0f1a24] border border-[#1e3a5f] 
          text-white text-sm rounded-lg px-4 py-2
          hover:bg-[#132636] hover:border-primary/30 transition-all duration-200
          ${isOpen ? "border-primary/50 bg-[#132636]" : ""}
        `}
      >
        <span className={value !== "all" ? "text-foreground" : ""}>{displayLabel}</span>
        <ChevronDown className={`w-4 h-4 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-48 bg-[#0f1a24] border border-[#1e3a5f] rounded-lg shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
          {options.map((option) => (
            <button
              key={option.value}
              onClick={() => {
                onChange(option.value)
                setIsOpen(false)
              }}
              className={`
                w-full flex items-center justify-between px-4 py-2.5 text-sm text-left
                transition-colors duration-150
                ${
                  option.value === value
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-[#132636] hover:text-foreground"
                }
              `}
            >
              <span>{option.label}</span>
              {option.value === value && <Check className="w-4 h-4" />}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
