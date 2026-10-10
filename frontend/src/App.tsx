import { useMutation, useQuery } from '@tanstack/react-query'
import { useCallback, useMemo, useState } from 'react'
import { fetchHeatmap, planTrip } from './api'
import CheckpointTable from './components/CheckpointTable'
import HeatmapControls from './components/HeatmapControls'
import MapView, { type ActiveCheckpoint } from './components/MapView'
import RouteList from './components/RouteList'
import TripForm from './components/TripForm'
import { downsample } from './geo'
import type { HeatMetric, Plan, PlanRequest } from './types'

export default function App() {
  const [plan, setPlan] = useState<Plan | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [active, setActive] = useState<ActiveCheckpoint | null>(null)
  const [hour, setHour] = useState(0)
  const [metric, setMetric] = useState<HeatMetric>('risk')
  const [playing, setPlaying] = useState(false)

  const planMutation = useMutation({
    mutationFn: planTrip,
    onSuccess: (data) => {
      setPlan(data)
      setSelectedId(data.recommendation.best_id)
      setActive(null)
      setHour(0)
      setPlaying(false)
    },
  })

  const heatBody = useMemo(
    () =>
      plan && {
        lines: plan.routes.map((r) => downsample(r.geometry, 300)),
        start: plan.departure,
        load_lb: plan.load_lb,
      },
    [plan],
  )

  const heatQuery = useQuery({
    queryKey: ['heatmap', heatBody],
    queryFn: ({ signal }) => fetchHeatmap(heatBody!, signal),
    enabled: !!heatBody,
  })

  const selectRoute = useCallback((id: string) => {
    setSelectedId(id)
    setActive((a) => (a && a.routeId !== id ? null : a))
  }, [])

  const pickCheckpoint = useCallback(
    (index: number) => selectedId && setActive({ routeId: selectedId, index }),
    [selectedId],
  )

  const { mutate } = planMutation
  const submitTrip = useCallback((req: PlanRequest) => mutate(req), [mutate])

  const selected = plan?.routes.find((r) => r.id === selectedId) ?? null

  return (
    <div className="app">
      <aside className="sidebar">
        <header>
          <h1>Climafeet</h1>
          <p>Weather-aware truck routing</p>
        </header>

        <TripForm busy={planMutation.isPending} onSubmit={submitTrip} />

        {planMutation.isError && <p className="form-error banner">{planMutation.error.message}</p>}

        {plan && selectedId && (
          <RouteList plan={plan} selectedId={selectedId} onSelect={selectRoute} onHover={setHoveredId} />
        )}

        {selected && (
          <CheckpointTable
            route={selected}
            activeIndex={active?.routeId === selected.id ? active.index : null}
            onPick={pickCheckpoint}
          />
        )}

        {!plan && !planMutation.isPending && (
          <p className="hint">
            Enter a trip to compare three truck routes. Each one is checked against the forecast at the
            time the truck would actually reach every checkpoint.
          </p>
        )}
      </aside>

      <main className="map-area">
        <div className="map-canvas">
          <MapView
            plan={plan}
            heatmap={heatQuery.data ?? null}
            hour={hour}
            metric={metric}
            selectedId={selectedId}
            hoveredId={hoveredId}
            active={active}
            onSelectRoute={selectRoute}
            onCheckpoint={setActive}
          />
          {planMutation.isPending && <div className="map-loading">Planning routes...</div>}
        </div>

        {plan && (
          <HeatmapControls
            start={heatQuery.data?.start ?? plan.departure}
            hour={hour}
            maxHour={heatQuery.data?.hours ?? 48}
            metric={metric}
            playing={playing}
            loading={heatQuery.isPending}
            error={heatQuery.isError ? heatQuery.error.message : null}
            onHour={setHour}
            onMetric={setMetric}
            onPlaying={setPlaying}
          />
        )}
      </main>
    </div>
  )
}
