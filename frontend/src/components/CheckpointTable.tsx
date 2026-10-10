import { memo } from 'react'
import { formatTime } from '../format'
import { levelColor } from '../risk'
import type { Route } from '../types'

interface Props {
  route: Route
  activeIndex: number | null
  onPick: (index: number) => void
}

function CheckpointTable({ route, activeIndex, onPick }: Props) {
  return (
    <details className="checkpoints" open>
      <summary>
        {route.name} checkpoints <span className="muted">({route.checkpoints.length})</span>
      </summary>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Mile</th>
              <th>ETA</th>
              <th>Risk</th>
              <th title="Sustained wind, mph">Wind</th>
              <th title="Rain, in/hr">Rain</th>
              <th title="Snow, in/hr">Snow</th>
            </tr>
          </thead>
          <tbody>
            {route.checkpoints.map((c, i) => (
              <tr
                key={c.mile}
                className={i === activeIndex ? 'active' : ''}
                onClick={() => onPick(i)}
                title={c.reasons.join(', ') || 'No weather concerns'}
              >
                <td>{Math.round(c.mile)}</td>
                <td>{formatTime(c.eta)}</td>
                <td>
                  <span className="dot" style={{ background: levelColor(c.level) }} />
                  {c.label}
                </td>
                <td>{c.weather.wind_mph.toFixed(0)}</td>
                <td>{c.weather.rain_in_hr.toFixed(2)}</td>
                <td>{c.weather.snow_in_hr.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

export default memo(CheckpointTable)
