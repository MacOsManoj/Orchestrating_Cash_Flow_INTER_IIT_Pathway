interface MarketContextCardProps {
  text: string
}

export function MarketContextCard({ text }: MarketContextCardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Market Context</h3>
      <p className="text-sm text-white/70 leading-relaxed">{text}</p>
    </div>
  )
}
