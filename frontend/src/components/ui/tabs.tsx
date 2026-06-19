import * as React from "react"
import { cn } from "@/lib/utils"

const Tabs = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("w-full", className)}
    {...props}
  />
))
Tabs.displayName = "Tabs"

const TabsList = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "inline-flex h-10 items-center justify-start bg-background border-b border-border w-full",
      className
    )}
    {...props}
  />
))
TabsList.displayName = "TabsList"

const TabsTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & {
    active?: boolean
    closeable?: boolean
    onClose?: (e: React.MouseEvent) => void
  }
>(({ className, active, closeable, onClose, children, ...props }, ref) => (
  <button
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap px-4 h-10 text-sm font-medium transition-all relative group",
      "hover:bg-card border-r border-border",
      active && "bg-card text-foreground border-b-2 border-b-accent -mb-[2px]",
      !active && "text-muted-foreground",
      className
    )}
    {...props}
  >
    <span className="mr-1">{children}</span>
    {closeable && (
      <button
        onClick={onClose}
        className={cn(
          "ml-1 transition-all rounded hover:bg-accent/20 p-0.5",
          active ? "opacity-60 hover:opacity-100" : "opacity-0 group-hover:opacity-60 group-hover:hover:opacity-100"
        )}
      >
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5">
          <path d="M3.5 3.5L10.5 10.5M10.5 3.5L3.5 10.5"/>
        </svg>
      </button>
    )}
  </button>
))
TabsTrigger.displayName = "TabsTrigger"

const TabsContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex-1 overflow-auto min-h-0", className)}
    {...props}
  />
))
TabsContent.displayName = "TabsContent"

export { Tabs, TabsList, TabsTrigger, TabsContent }
