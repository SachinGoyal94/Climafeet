import { useEffect } from 'react'
import { formatDateTime } from '../format'
import { LEVELS, METRICS } from '../risk'
import type { HeatMetric } from '../types'

interface Props {
  start: string
  hour: number
  maxHour: number
  metric: HeatMetric
  playing: boolean
  loading: boolean
  error: string | null
  onHour: (h: number) => void
  onMetric: (m: HeatMetric) => void
  onPlaying: (p: boolean) => void
}

export default function HeatmapControls(props: Props) {
  const { start, hour, maxHour, metric, playing, loading, error } = props
  const { onHour, onMetric, onPlaying } = props

  useEffect(() => {
    if (!playing) return
    const t = window.setInterval(() => onHour((hour + 1) % (maxHour + 1)), 450)
    return () => window.clearInterval(t)
  }, [playing, hour, maxHour, onHour])

  const at = new Date(new Date(start).getTime() + hour * 3600 * 1000)
  const scale = METRICS[metric]

  return (
    <div className="heat-controls">
      <div className="heat-top">
        <button
          type="button"
          className="play"
          onClick={() => onPlaying(!playing)}
          aria-label={playing ? 'Pause' : 'Play'}
          disabled={loading || !!error}
        >
          {playing ? '\u275A\u275A' : '\u25B6'}
        </button>
        <div className="heat-time">
          <strong>+{hour}h</strong> <span>{formatDateTime(at)}</span>
        </div>
        <select value={metric} onChange={(e) => onMetric(e.target.value as HeatMetric)}>
          {(Object.keys(METRICS) as HeatMetric[]).map((m) => (
            <option key={m} value={m}>
              {METRICS[m].label}
            </option>
          ))}
        </select>
      </div>

      <input
        type="range"
        min={0}
        max={maxHour}
        step={1}
        value={hour}
        onChange={(e) => {
          onPlaying(false)
          onHour(Number(e.target.value))
        }}
        aria-label="Forecast hour"
        disabled={loading || !!error}
      />

      <div className="heat-legend">
        {loading && <span className="muted">Loading corridor forecast...</span>}
        {error && <span className="form-error">{error}</span>}
        {!loading &&
          !error &&
          LEVELS.map((l, i) => (
            <span key={l.label}>
              <i style={{ background: l.color }} />
              {metric === 'risk' ? l.label : `${scale.bands[i]}+ ${scale.unit}`}
            </span>
          ))}
      </div>
    </div>
  )
}
