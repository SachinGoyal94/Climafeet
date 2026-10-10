import { formatMiles } from '../format'
import { LEVELS } from '../risk'
import type { RouteSummary } from '../types'

export default function RiskBar({ summary, total }: { summary: RouteSummary; total: number }) {
  return (
    <div className="risk-bar" aria-label="Miles by risk level">
      {LEVELS.map(({ label, color }) => {
        const mi = summary.miles[label]
        if (!mi) return null
        return (
          <span
            key={label}
            style={{ width: `${(mi / total) * 100}%`, background: color }}
            title={`${label}: ${formatMiles(mi)}`}
          />
        )
      })}
    </div>
  )
}
