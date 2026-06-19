interface ProsConsSectionProps {
  pros: string[]
  cons: string[]
}

export function ProsConsSection({ pros, cons }: ProsConsSectionProps) {
  return (
    <div className="grid grid-cols-2 gap-4">
      {/* PROS */}
      <div className="border border-teal-700/50 rounded-lg p-6 bg-[#0a2428] min-h-[160px]">
        <h3 className="text-lg font-semibold text-emerald-500 mb-4">PROS:</h3>
        {pros.length > 0 ? (
          <ul className="space-y-2 text-gray-300">
            {pros.map((pro, index) => (
              <li key={index}>• {pro}</li>
            ))}
          </ul>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500">No data available</div>
        )}
      </div>

      {/* CONS */}
      <div className="border border-teal-700/50 rounded-lg p-6 bg-[#0a2428] min-h-[160px]">
        <h3 className="text-lg font-semibold text-red-500 mb-4">CONS:</h3>
        {cons.length > 0 ? (
          <ul className="space-y-2 text-gray-300">
            {cons.map((con, index) => (
              <li key={index}>• {con}</li>
            ))}
          </ul>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-500">No data available</div>
        )}
      </div>
    </div>
  )
}
