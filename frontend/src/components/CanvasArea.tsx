// src/components/CanvasArea.tsx
import React from "react"
import { usePlayground } from "../context/PlaygroundContext"
import {
  type CanvasItem,
  buildCanvasRows,
  sizeToCols,
  type ComponentSize,
} from "./CanvasLayout"
import { ComponentRegistry } from "./playground-components"

type RawComponents = any

function normalizeComponents(raw: RawComponents): CanvasItem[] {
  if (!raw) return []

  let entries: any[] = []

  if (Array.isArray(raw)) {
    entries = raw
  } else if (typeof raw === "object") {
    entries = Object.entries(raw).map(([id, value]) => ({
      id,
      ...(value as any),
    }))
  } else {
    return []
  }

  const mapped = entries.map((item: any, index: number): CanvasItem | null => {
    const type: string | undefined = item.type
    if (!type) return null

    const def = ComponentRegistry[type]
    const size: ComponentSize = def?.defaultSize ?? "medium"

    const base: CanvasItem = {
      id: item.id ?? `comp-${index}`,
      type,
      size,
    }

    if (item.data !== undefined) {
      ;(base as any).data = item.data
    }

    return base
  })

  return mapped.filter((x): x is CanvasItem => x !== null)
}

export const CanvasArea: React.FC = () => {
  const { currentVersion, isLoading } = usePlayground()

  if (!currentVersion) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[#0f1419] p-3 sm:p-4 md:p-6">
        <div className="text-center">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-3 text-white">
            Ready to begin?
          </h1>
          <p className="text-gray-400 text-sm sm:text-base md:text-lg">Explore with Playground</p>
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[#0f1419]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto mb-4" />
          <p className="text-gray-400 text-sm">Generating canvas...</p>
        </div>
      </div>
    )
  }

  const items: CanvasItem[] = normalizeComponents(currentVersion.components)
  const rows = buildCanvasRows(items)

  return (
    <main className="flex-1 overflow-auto bg-[#0a0e14] p-2 sm:p-2 md:p-3">
      <div className="w-full max-w-7xl mx-auto">
        {/* Version header - compact */}
        <div className="mb-2 sm:mb-3 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
          <div className="min-w-0">
            <h2 className="text-base sm:text-lg md:text-xl font-semibold text-white truncate">
              Version {currentVersion.versionNumber}
            </h2>
            {currentVersion.prompt && (
              <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">
                {currentVersion.prompt}
              </p>
            )}
          </div>
        </div>

        {/* Rows - minimal gap */}
        {rows.length > 0 ? (
          <div className="space-y-1 sm:space-y-1.5 md:space-y-2">
            {rows.map((row) => (
              <div 
                key={row.id} 
                className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-1 sm:gap-1.5 md:gap-2"
              >
                {row.items.map((item) => {
                  const def = ComponentRegistry[item.type]
                  if (!def) {
                    return (
                      <div
                        key={item.id}
                        className="col-span-1 bg-red-900/20 border border-red-700 rounded-lg p-2 sm:p-3"
                      >
                        <p className="text-red-400 font-semibold text-xs sm:text-sm">⚠️ Not Found</p>
                        <p className="text-red-300 text-[10px] mt-0.5">
                          "{item.type}"
                        </p>
                      </div>
                    )
                  }

                  const Component = def.component
                  const cols = sizeToCols(item.size)
                  
                  let colClass = "col-span-1"
                  if (cols === 4) {
                    colClass = "col-span-1 sm:col-span-2 md:col-span-4"
                  } else if (cols === 3) {
                    colClass = "col-span-1 sm:col-span-2 md:col-span-3"
                  } else if (cols === 2) {
                    colClass = "col-span-1 sm:col-span-2 md:col-span-2"
                  }

                  return (
                    <div key={item.id} className={colClass}>
                      <Component {...(item.data ?? {})} />
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-6 sm:py-8">
            <p className="text-gray-500 text-xs sm:text-sm">No components</p>
          </div>
        )}
      </div>
    </main>
  )
}
