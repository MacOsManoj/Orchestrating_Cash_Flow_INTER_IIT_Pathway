// src/components/CanvasLayout.ts
import type React from "react"

export type ComponentSize = "full" | "large" | "medium" | "small"

export interface CanvasItem {
  id: string
  type: string
  size: ComponentSize
  data?: any
}

export interface CanvasRow {
  id: string
  items: CanvasItem[]
}

export interface CanvasComponentDefinition {
  component: React.ComponentType<any>
  defaultSize: ComponentSize
}

/**
 * Map our logical size → grid columns (4-col layout).
 * - full  => 4/4 (whole row)
 * - large => 3/4
 * - medium => 1/2 (2 per row)
 * - small => 1/4 (4 per row)
 */
export function sizeToCols(size: ComponentSize): number {
  switch (size) {
    case "full":
      return 4
    case "large":
      return 3
    case "medium":
      return 2
    case "small":
    default:
      return 1
  }
}

/**
 * Build rows based on size with this priority:
 * 1) full (4/4)
 * 2) large (3/4) + small (1/4)
 * 3) medium (2/4) + medium (2/4)
 * 4) medium (2/4) + small (1/4) + small (1/4)
 * 5) remaining small (up to 4 per row)
 * 6) remaining medium (up to 2 per row)
 * 7) remaining large (alone per row)
 */
export function buildCanvasRows(items: CanvasItem[]): CanvasRow[] {
  const full: CanvasItem[] = []
  const large: CanvasItem[] = []
  const medium: CanvasItem[] = []
  const small: CanvasItem[] = []

  // bucket by size
  for (const item of items) {
    switch (item.size) {
      case "full":
        full.push(item)
        break
      case "large":
        large.push(item)
        break
      case "medium":
        medium.push(item)
        break
      case "small":
      default:
        small.push(item)
        break
    }
  }

  const rows: CanvasRow[] = []
  let rowCounter = 1

  let fullIdx = 0
  let largeIdx = 0
  let mediumIdx = 0
  let smallIdx = 0

  // 1) full-width rows (4/4)
  while (fullIdx < full.length) {
    rows.push({
      id: `row-${rowCounter++}`,
      items: [full[fullIdx++]],
    })
  }

  // 2) large (3/4) + small (1/4)
  while (largeIdx < large.length) {
    const rowItems: CanvasItem[] = [large[largeIdx++]]
    if (smallIdx < small.length) {
      rowItems.push(small[smallIdx++])
    }
    rows.push({
      id: `row-${rowCounter++}`,
      items: rowItems,
    })
  }

  // 3) medium (2/4) + medium (2/4)
  while (mediumIdx + 1 < medium.length) {
    const rowItems: CanvasItem[] = [medium[mediumIdx++], medium[mediumIdx++]]
    rows.push({
      id: `row-${rowCounter++}`,
      items: rowItems,
    })
  }

  // 4) medium (2/4) + small (1/4) + small (1/4)
  while (mediumIdx < medium.length && smallIdx + 1 < small.length) {
    const rowItems: CanvasItem[] = [
      medium[mediumIdx++],
      small[smallIdx++],
      small[smallIdx++],
    ]
    rows.push({
      id: `row-${rowCounter++}`,
      items: rowItems,
    })
  }

  // 5) remaining small → rows of up to 4
  while (smallIdx < small.length) {
    const rowItems: CanvasItem[] = []
    let capacity = 4

    while (capacity > 0 && smallIdx < small.length) {
      rowItems.push(small[smallIdx++])
      capacity--
    }

    rows.push({
      id: `row-${rowCounter++}`,
      items: rowItems,
    })
  }

  // 6) remaining medium → rows of up to 2
  while (mediumIdx < medium.length) {
    const rowItems: CanvasItem[] = []
    let capacity = 2

    while (capacity > 0 && mediumIdx < medium.length) {
      rowItems.push(medium[mediumIdx++])
      capacity--
    }

    rows.push({
      id: `row-${rowCounter++}`,
      items: rowItems,
    })
  }

  // 7) any remaining large → alone per row
  while (largeIdx < large.length) {
    rows.push({
      id: `row-${rowCounter++}`,
      items: [large[largeIdx++]],
    })
  }

  return rows
}
