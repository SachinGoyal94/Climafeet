import type { FeatureCollection } from 'geojson'
import * as maplibregl from 'maplibre-gl'
import { setWorkerUrl } from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import type { ExpressionSpecification } from 'maplibre-gl'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Map, {
  Layer,
  Marker,
  NavigationControl,
  Popup,
  ScaleControl,
  Source,
  type MapLayerMouseEvent,
  type MapRef,
} from 'react-map-gl/maplibre'
import { formatMiles, formatDuration, formatTime } from '../format'
import { cumulativeMiles, pointAtFraction, truckPosition } from '../geo'
import { LEVELS, ROUTE_COLORS, heatColorStops, heatWeight, levelColor } from '../risk'
import type { HeatMetric, Heatmap, Plan } from '../types'

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

// MapLibre otherwise looks for its worker beside its module, which breaks in Vite's bundle.
setWorkerUrl(maplibreWorkerUrl)

const METRIC_PREFIX: Record<HeatMetric, string> = {
  risk: 'r',
  wind_mph: 'w',
  rain_in_hr: 'p',
  snow_in_hr: 's',
}
const LABEL_AT = [0.42, 0.55, 0.68]

export interface ActiveCheckpoint {
  routeId: string
  index: number
}

interface Props {
  plan: Plan | null
  heatmap: Heatmap | null
  hour: number
  metric: HeatMetric
  selectedId: string | null
  hoveredId: string | null
  active: ActiveCheckpoint | null
  onSelectRoute: (id: string) => void
  onCheckpoint: (c: ActiveCheckpoint | null) => void
}

const levelMatch = [
  'match',
  ['get', 'level'],
  ...LEVELS.flatMap((l, i) => [i, l.color]),
  '#888',
] as unknown as ExpressionSpecification

export default function MapView(props: Props) {
  const { plan, heatmap, hour, metric, selectedId, hoveredId, active } = props
  const { onSelectRoute, onCheckpoint } = props
  const mapRef = useRef<MapRef>(null)
  const [loaded, setLoaded] = useState(false)
  const [firstSymbol, setFirstSymbol] = useState<string | undefined>()
  const [cursor, setCursor] = useState('')

  const routeCums = useMemo(
    () => plan?.routes.map((r) => cumulativeMiles(r.geometry)) ?? [],
    [plan],
  )

  const routesGeo = useMemo<FeatureCollection>(
    () => ({
      type: 'FeatureCollection',
      features: (plan?.routes ?? []).map((r) => ({
        type: 'Feature',
        properties: { id: r.id, color: ROUTE_COLORS[r.id] },
        geometry: { type: 'LineString', coordinates: r.geometry },
      })),
    }),
    [plan],
  )

  const checkpointsGeo = useMemo<FeatureCollection>(
    () => ({
      type: 'FeatureCollection',
      features: (plan?.routes ?? []).flatMap((r) =>
        r.checkpoints.map((c, i) => ({
          type: 'Feature' as const,
          properties: { route: r.id, index: i, level: c.level },
          geometry: { type: 'Point' as const, coordinates: [c.lon, c.lat] },
        })),
      ),
    }),
    [plan],
  )

  // Every hour and metric is baked into the feature properties up front. Moving the
  // slider then only swaps the paint expression, so nothing is re-uploaded to the GPU.
  const heatGeo = useMemo<FeatureCollection | null>(() => {
    if (!heatmap) return null
    return {
      type: 'FeatureCollection',
      features: heatmap.cells.map((coords, ci) => {
        const properties: Record<string, number> = {}
        for (const m of Object.keys(METRIC_PREFIX) as HeatMetric[]) {
          const rows = heatmap[m]
          for (let h = 0; h <= heatmap.hours; h++) {
            properties[`${METRIC_PREFIX[m]}${h}`] = heatWeight(m, rows[h][ci])
          }
        }
        return { type: 'Feature', properties, geometry: { type: 'Point', coordinates: coords } }
      }),
    }
  }, [heatmap])

  const trucksGeo = useMemo<FeatureCollection>(() => {
    if (!plan || !heatmap) return { type: 'FeatureCollection', features: [] }
    const ms = Date.parse(heatmap.start) + hour * 3600 * 1000
    return {
      type: 'FeatureCollection',
      features: plan.routes.map((r, i) => {
        const { pos, state } = truckPosition(r, routeCums[i], ms)
        return {
          type: 'Feature',
          properties: { id: r.id, color: ROUTE_COLORS[r.id], state },
          geometry: { type: 'Point', coordinates: pos },
        }
      }),
    }
  }, [plan, heatmap, hour, routeCums])

  const fitPlan = useCallback(() => {
    if (!plan || !mapRef.current) return
    const [w, s, e, n] = plan.bbox
    // the heatmap controls float over the bottom of the map on wide screens only
    const bottom = window.matchMedia('(max-width: 860px)').matches ? 40 : 190
    mapRef.current.fitBounds(
      [
        [w, s],
        [e, n],
      ],
      { padding: { top: 70, bottom, left: 50, right: 50 }, duration: 900 },
    )
  }, [plan])

  useEffect(() => {
    if (loaded) fitPlan()
  }, [loaded, fitPlan])

  const activeCp = useMemo(() => {
    if (!plan || !active) return null
    const route = plan.routes.find((r) => r.id === active.routeId)
    const cp = route?.checkpoints[active.index]
    return route && cp ? { route, cp } : null
  }, [plan, active])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !activeCp) return
    const { lon, lat } = activeCp.cp
    if (!map.getBounds().contains([lon, lat])) map.easeTo({ center: [lon, lat], duration: 600 })
  }, [activeCp])

  function handleLoad() {
    const layers = mapRef.current?.getStyle().layers ?? []
    setFirstSymbol(layers.find((l) => l.type === 'symbol')?.id)
    setLoaded(true)
  }

  function handleClick(e: MapLayerMouseEvent) {
    const f = e.features?.[0]
    if (!f) {
      onCheckpoint(null)
      return
    }
    if (f.layer.id === 'checkpoints') {
      onCheckpoint({ routeId: f.properties.route, index: f.properties.index })
    } else {
      onSelectRoute(f.properties.id)
    }
  }

  const sel = selectedId ?? ''
  const hov = hoveredId ?? ''
  const isSel: ExpressionSpecification = ['==', ['get', 'id'], sel]
  const isHov: ExpressionSpecification = ['==', ['get', 'id'], hov]
  const cpOnSel: ExpressionSpecification = ['==', ['get', 'route'], sel]

  // keep the kernel radius tied to the grid spacing so the field looks the same at every zoom
  const radius0 = heatmap ? (heatmap.step_deg / 360) * 512 * 2 : 1

  return (
    <Map
      ref={mapRef}
      mapLib={maplibregl}
      initialViewState={{ longitude: -96, latitude: 39, zoom: 3.6 }}
      mapStyle={MAP_STYLE}
      onLoad={handleLoad}
      interactiveLayerIds={plan ? ['checkpoints', 'route-hit'] : []}
      onClick={handleClick}
      onMouseEnter={() => setCursor('pointer')}
      onMouseLeave={() => setCursor('')}
      cursor={cursor}
      style={{ position: 'absolute', inset: 0 }}
      attributionControl={{ compact: true }}
    >
      <NavigationControl position="top-right" showCompass={false} />
      <ScaleControl position="top-left" unit="imperial" />

      {heatGeo && (
        <Source id="heat" type="geojson" data={heatGeo}>
          <Layer
            id="heat"
            type="heatmap"
            beforeId={firstSymbol}
            paint={{
              'heatmap-weight': ['get', `${METRIC_PREFIX[metric]}${hour}`],
              'heatmap-radius': ['interpolate', ['exponential', 2], ['zoom'], 0, radius0, 14, radius0 * 2 ** 14],
              'heatmap-intensity': 0.9,
              'heatmap-opacity': 0.62,
              'heatmap-color': [
                'interpolate',
                ['linear'],
                ['heatmap-density'],
                ...heatColorStops(metric),
              ] as unknown as ExpressionSpecification,
            }}
          />
        </Source>
      )}

      {plan && (
        <Source id="routes" type="geojson" data={routesGeo}>
          <Layer
            id="route-casing"
            type="line"
            layout={{ 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['case', isSel, 2, isHov, 1, 0] }}
            paint={{ 'line-color': '#ffffff', 'line-width': ['case', isSel, 10, isHov, 8, 6] }}
          />
          <Layer
            id="route-line"
            type="line"
            layout={{ 'line-join': 'round', 'line-cap': 'round', 'line-sort-key': ['case', isSel, 2, isHov, 1, 0] }}
            paint={{
              'line-color': ['get', 'color'],
              'line-width': ['case', isSel, 6, isHov, 5, 3.5],
              'line-opacity': ['case', isSel, 1, isHov, 0.9, 0.55],
            }}
          />
          <Layer id="route-hit" type="line" paint={{ 'line-width': 16, 'line-opacity': 0 }} />
        </Source>
      )}

      {plan && (
        <Source id="checkpoints" type="geojson" data={checkpointsGeo}>
          <Layer
            id="checkpoints"
            type="circle"
            layout={{ 'circle-sort-key': ['case', cpOnSel, 1, 0] }}
            paint={{
              'circle-color': levelMatch,
              'circle-radius': ['interpolate', ['linear'], ['zoom'], 3, ['case', cpOnSel, 4, 2.5], 9, ['case', cpOnSel, 8, 5]],
              'circle-stroke-color': '#ffffff',
              'circle-stroke-width': ['case', cpOnSel, 1.5, 0.5],
              'circle-opacity': ['case', cpOnSel, 1, 0.55],
              'circle-stroke-opacity': ['case', cpOnSel, 1, 0.55],
            }}
          />
        </Source>
      )}

      {plan && heatmap && (
        <Source id="trucks" type="geojson" data={trucksGeo}>
          <Layer
            id="trucks"
            type="circle"
            paint={{
              'circle-radius': 7,
              'circle-color': ['get', 'color'],
              'circle-stroke-color': '#111827',
              'circle-stroke-width': 2.5,
              'circle-opacity': ['case', ['==', ['get', 'state'], 'driving'], 1, 0.45],
            }}
          />
        </Source>
      )}

      {plan && (
        <>
          <Marker longitude={plan.origin.lon} latitude={plan.origin.lat} anchor="center">
            <div className="pin origin" title={plan.origin.label} />
          </Marker>
          <Marker longitude={plan.destination.lon} latitude={plan.destination.lat} anchor="center">
            <div className="pin dest" title={plan.destination.label} />
          </Marker>
          {plan.routes.map((r, i) => {
            const [lon, lat] = pointAtFraction(r.geometry, routeCums[i], LABEL_AT[i] ?? 0.5)
            return (
              <Marker key={r.id} longitude={lon} latitude={lat} anchor="bottom">
                <button
                  type="button"
                  className={`route-label ${r.id === selectedId ? 'selected' : ''}`}
                  style={{ borderColor: ROUTE_COLORS[r.id] }}
                  onClick={(e) => {
                    e.stopPropagation()
                    onSelectRoute(r.id)
                  }}
                >
                  <b style={{ color: ROUTE_COLORS[r.id] }}>{r.id}</b>
                  {formatMiles(r.distance_miles)} &middot; {formatDuration(r.duration_s)}
                  <i style={{ background: levelColor(r.summary.max_level) }} title={`Worst: ${r.summary.max_label}`} />
                  {r.recommended && <em>Best</em>}
                </button>
              </Marker>
            )
          })}
        </>
      )}

      {activeCp && (
        <Popup
          longitude={activeCp.cp.lon}
          latitude={activeCp.cp.lat}
          anchor="bottom"
          offset={10}
          closeOnClick={false}
          onClose={() => onCheckpoint(null)}
          maxWidth="260px"
        >
          <div className="cp-popup">
            <div className="cp-head">
              <span>
                {activeCp.route.name} &middot; mile {Math.round(activeCp.cp.mile)}
              </span>
              <span className="chip" style={{ background: levelColor(activeCp.cp.level) }}>
                {activeCp.cp.label}
              </span>
            </div>
            <div className="muted">ETA {formatTime(activeCp.cp.eta)}</div>
            <dl>
              <dt>Wind</dt>
              <dd>
                {activeCp.cp.weather.wind_mph.toFixed(0)} mph (gusts {activeCp.cp.weather.gust_mph.toFixed(0)})
              </dd>
              <dt>Rain</dt>
              <dd>{activeCp.cp.weather.rain_in_hr.toFixed(2)} in/hr</dd>
              <dt>Snow</dt>
              <dd>{activeCp.cp.weather.snow_in_hr.toFixed(2)} in/hr</dd>
              <dt>Temp</dt>
              <dd>{activeCp.cp.weather.temp_f.toFixed(0)}&deg;F</dd>
            </dl>
            {activeCp.cp.reasons.length > 0 && <p className="cp-reasons">{activeCp.cp.reasons.join(', ')}</p>}
          </div>
        </Popup>
      )}
    </Map>
  )
}
