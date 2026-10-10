import { useState } from 'react'
import { defaultDeparture, toLocalInput } from '../format'
import type { Place, PlanRequest } from '../types'
import PlaceInput from './PlaceInput'

interface Props {
  busy: boolean
  onSubmit: (req: PlanRequest) => void
}

const INTERVALS = [10, 25, 50] as const

export default function TripForm({ busy, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place>({ label: '' })
  const [destination, setDestination] = useState<Place>({ label: '' })
  const [departure, setDeparture] = useState(() => toLocalInput(defaultDeparture()))
  const [load, setLoad] = useState('38000')
  const [spacing, setSpacing] = useState<(typeof INTERVALS)[number]>(25)
  const [error, setError] = useState<string | null>(null)
  const [bounds] = useState(() => {
    const now = Date.now()
    return {
      min: toLocalInput(new Date(now)),
      max: toLocalInput(new Date(now + 7 * 24 * 3600 * 1000)),
    }
  })

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const loadLb = Number(load)
    if (!origin.label.trim() || !destination.label.trim()) {
      setError('Enter both an origin and a destination.')
      return
    }
    if (!Number.isFinite(loadLb) || loadLb < 0 || loadLb > 100000) {
      setError('Load weight must be between 0 and 100,000 lb.')
      return
    }
    const dep = new Date(departure)
    if (Number.isNaN(dep.getTime())) {
      setError('Pick a departure date and time.')
      return
    }
    setError(null)
    onSubmit({
      origin,
      destination,
      departure: dep.toISOString(),
      load_lb: loadLb,
      interval_miles: spacing,
    })
  }

  function swap() {
    setOrigin(destination)
    setDestination(origin)
  }

  return (
    <form className="trip-form" onSubmit={submit} noValidate>
      <div className="places">
        <PlaceInput label="Origin" value={origin} onChange={setOrigin} placeholder="e.g. Chicago, IL" />
        <button type="button" className="swap" onClick={swap} title="Swap origin and destination">
          &#8645;
        </button>
        <PlaceInput
          label="Destination"
          value={destination}
          onChange={setDestination}
          placeholder="e.g. Denver, CO"
        />
      </div>

      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={departure}
            min={bounds.min}
            max={bounds.max}
            onChange={(e) => setDeparture(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={0}
            max={100000}
            step={500}
            value={load}
            onChange={(e) => setLoad(e.target.value)}
          />
        </div>
      </div>

      <div className="field">
        <span className="label">Weather checkpoint every</span>
        <div className="segmented" role="radiogroup" aria-label="Checkpoint interval">
          {INTERVALS.map((i) => (
            <button
              key={i}
              type="button"
              role="radio"
              aria-checked={spacing === i}
              className={spacing === i ? 'on' : ''}
              onClick={() => setSpacing(i)}
            >
              {i} mi
            </button>
          ))}
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}

      <button type="submit" className="primary" disabled={busy}>
        {busy ? 'Checking routes and forecasts...' : 'Find safest route'}
      </button>
    </form>
  )
}
