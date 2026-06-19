"use client"

import { useState } from "react"

interface CategoryFilterProps {
  categories: string[]
  activeCategory: string
  onCategoryChange: (category: string) => void
}

export function CategoryFilter({ categories, activeCategory, onCategoryChange }: CategoryFilterProps) {
  const [hoveredCategory, setHoveredCategory] = useState<string | null>(null)

  return (
    <div className="flex gap-2">
      {categories.map((category) => (
        <button
          key={category}
          onClick={() => onCategoryChange(category)}
          onMouseEnter={() => setHoveredCategory(category)}
          onMouseLeave={() => setHoveredCategory(null)}
          className={`px-4 py-1.5 rounded-full text-sm transition-all duration-300 transform
            ${
              activeCategory === category
                ? "bg-primary text-white scale-105 shadow-lg shadow-primary/30"
                : hoveredCategory === category
                  ? "bg-white/10 text-white -translate-y-0.5"
                  : "bg-white/5 text-white/70"
            }`}
        >
          {category}
        </button>
      ))}
    </div>
  )
}
