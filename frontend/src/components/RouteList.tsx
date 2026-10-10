import { formatDuration, formatMiles, formatTime } from '../format'
import { LEVELS, ROUTE_COLORS, levelColor } from '../risk'
import type { Plan } from '../types'
import RiskBar from './RiskBar'

interface Props {
  plan: Plan
  selectedId: string
  onSelect: (id: string) => void
  onHover: (id: string | null) => void
}

export default function RouteList({ plan, selectedId, onSelect, onHover }: Props) {
  const { recommendation: rec } = plan
  const best = plan.routes.find((r) => r.id === rec.best_id)!
  const ordered = [...plan.routes].sort((a, b) => a.rank - b.rank)

  return (
    <section className="routes">
      <div className={`recommend ${rec.warning ? 'has-warning' : ''}`}>
        <div className="recommend-title">
          Recommended: <strong>{best.name}</strong>
        </div>
        <p>{rec.reason}</p>
        {rec.warning && <p className="warning">{rec.warning}</p>}
      </div>

      {ordered.map((r) => {
        const s = r.summary
        const riskyMiles = s.miles['Severe'] + s.miles['No Travel']
        return (
          <button
            key={r.id}
            type="button"
            className={`route-card ${r.id === selectedId ? 'selected' : ''}`}
            style={{ '--route-color': ROUTE_COLORS[r.id] } as React.CSSProperties}
            onClick={() => onSelect(r.id)}
            onMouseEnter={() => onHover(r.id)}
            onMouseLeave={() => onHover(null)}
          >
            <div className="route-head">
              <span className="route-name">
                <i className="swatch" />
                {r.name}
              </span>
              {r.recommended && <span className="badge">Best</span>}
              <span className="rank">#{r.rank}</span>
            </div>

            <div className="route-stats">
              <span>{formatMiles(r.distance_miles)}</span>
              <span>{formatDuration(r.duration_s)}</span>
              <span>Arrive {formatTime(r.arrival)}</span>
            </div>

            <RiskBar summary={s} total={r.distance_miles} />

            <div className="route-risk">
              <span className="chip" style={{ background: levelColor(s.max_level) }}>
                Worst: {s.max_label}
              </span>
              <span>Avg risk {s.avg_risk.toFixed(2)}</span>
              {riskyMiles > 0 && <span className="danger">{formatMiles(riskyMiles)} severe+</span>}
              {s.miles['High'] > 0 && <span>{formatMiles(s.miles['High'])} high</span>}
            </div>
          </button>
        )
      })}

      <ul className="legend-inline">
        {LEVELS.map((l) => (
          <li key={l.label}>
            <i style={{ background: l.color }} />
            {l.label}
          </li>
        ))}
      </ul>
    </section>
  )
}
