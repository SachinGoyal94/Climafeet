import { useMutation, useQuery } from '@tanstack/react-query'
import { lazy, Suspense, useCallback, useMemo, useState } from 'react'
import { fetchHeatmap, planTrip } from './api'
import CheckpointTable from './components/CheckpointTable'
import HeatmapControls from './components/HeatmapControls'
import type { ActiveCheckpoint } from './components/MapView'
import RouteList from './components/RouteList'
import TripForm from './components/TripForm'
import LandingHero from './components/LandingHero'
import { downsample } from './geo'
import type { HeatMetric, Plan, PlanRequest } from './types'

const MapView = lazy(() => import('./components/MapView'))

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
    <div className="site-shell" id="top">
      <LandingHero />

      <section className="planner-section" id="planner" aria-labelledby="planner-title">
        <div className="section-heading planner-heading">
          <div>
            <p className="eyebrow">THE ROUTE WORKSPACE</p>
            <h2 id="planner-title">Plan for the road ahead.</h2>
            <p>Set your trip, compare truck routes, and see the forecast where it matters.</p>
          </div>
          <a className="text-link" href="#approach">
            How Climafeet works <span aria-hidden="true">↓</span>
          </a>
        </div>

        <div className="app">
          <aside className="sidebar" aria-label="Trip setup and route results">
            <div className="workspace-title">
              <span className="workspace-index" aria-hidden="true">01</span>
              <div>
                <p className="eyebrow">TRIP SETUP</p>
                <h3>Build your route</h3>
                <p>Tell us where you’re going and what you’re carrying.</p>
              </div>
            </div>

            <TripForm busy={planMutation.isPending} onSubmit={submitTrip} />

            {planMutation.isError && (
              <p className="form-error banner" role="alert">{planMutation.error.message}</p>
            )}

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
              <div className="empty-note">
                <span className="empty-note-icon" aria-hidden="true">↗</span>
                <p>Enter a trip to compare truck routes. Each route is checked against the forecast at the time the truck reaches each checkpoint.</p>
              </div>
            )}
          </aside>

          <main className="map-area" aria-label="Route map and forecast">
            <div className="map-toolbar">
              <div>
                <p className="eyebrow">ROUTE MAP</p>
                <strong>
                  {plan ? `${plan.origin.label} → ${plan.destination.label}` : 'Your trip will appear here'}
                </strong>
              </div>
              <span className="map-state">
                <i aria-hidden="true" />
                {plan ? `${plan.routes.length} routes compared` : 'Interactive map'}
              </span>
            </div>

            <div className="map-canvas">
              <Suspense fallback={<div className="map-loading" role="status">Loading map…</div>}>
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
              </Suspense>
              {planMutation.isPending && <div className="map-loading" role="status">Planning routes…</div>}
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
      </section>

      <section className="approach-section" id="approach" aria-labelledby="approach-title">
        <div className="section-heading approach-heading">
          <div>
            <p className="eyebrow">HOW IT WORKS</p>
            <h2 id="approach-title">A clearer picture of every mile.</h2>
            <p>Bring routing, load, and changing weather into one practical view.</p>
          </div>
          <span className="approach-aside">Weather-aware decisions, from departure to arrival.</span>
        </div>

        <div className="feature-grid">
          <article className="feature-card">
            <span className="feature-index">01 <i /> ROUTE OPTIONS</span>
            <h3>Compare truck routes</h3>
            <p>Review up to three truck-ready alternatives with distance, drive time, arrival time, and weather exposure side by side.</p>
            <span className="feature-arrow" aria-hidden="true">↗</span>
          </article>
          <article className="feature-card">
            <span className="feature-index">02 <i /> CHECKPOINT WEATHER</span>
            <h3>Forecast the trip as it unfolds</h3>
            <p>Estimate conditions at the truck’s arrival time along the route, with load-aware risk levels for wind, rain, and snow.</p>
            <span className="feature-arrow" aria-hidden="true">↗</span>
          </article>
          <article className="feature-card">
            <span className="feature-index">03 <i /> CORRIDOR VIEW</span>
            <h3>Explore the next 48 hours</h3>
            <p>Move through time and switch between overall risk, wind, rain, and snow to scan conditions across the route corridor.</p>
            <span className="feature-arrow" aria-hidden="true">↗</span>
          </article>
        </div>
      </section>

      <footer className="site-footer">
        <a className="footer-brand" href="#top">Climafeet<span>®</span></a>
        <span>Weather-aware truck routing</span>
        <a href="#planner">Plan a route <span aria-hidden="true">↑</span></a>
      </footer>
    </div>
  )
}
