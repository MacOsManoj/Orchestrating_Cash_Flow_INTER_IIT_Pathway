import { Button } from "@/components/ui/button"
import { ChevronDown } from "lucide-react"

interface CommodityHeaderProps {
  name: string
  symbol: string
}

export function CommodityHeader({ name, symbol }: CommodityHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <h1 className="text-4xl font-semibold text-white">
        {name} ({symbol})
      </h1>

      <div className="flex items-center gap-3">
        <Button className="bg-primary hover:bg-primary/80 text-white px-8 h-11 rounded-lg font-medium">Buy</Button>

        <Button className="bg-destructive hover:bg-destructive/80 text-white px-8 h-11 rounded-lg font-medium">Sell</Button>

        <Button
          variant="outline"
          className="border-accent text-success hover:bg-accent/10 px-6 h-11 rounded-lg font-medium bg-transparent"
        >
          Compare
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}
