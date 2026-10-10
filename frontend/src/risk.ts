import type { HeatMetric, RiskLabel } from './types'

export const LEVELS: { label: RiskLabel; color: string }[] = [
  { label: 'Low', color: '#2f9e5b' },
  { label: 'Moderate', color: '#e3b505' },
  { label: 'High', color: '#f07d1a' },
  { label: 'Severe', color: '#d62839' },
  { label: 'No Travel', color: '#6b1d8f' },
]

export const levelColor = (level: number) => LEVELS[Math.max(0, Math.min(4, level))].color

export const ROUTE_COLORS: Record<string, string> = {
  A: '#2563eb',
  B: '#0d9488',
  C: '#9333ea',
}

interface MetricScale {
  label: string
  unit: string
  max: number
  // value where each risk band starts, same thresholds the backend classifies with
  bands: number[]
}

export const METRICS: Record<HeatMetric, MetricScale> = {
  risk: { label: 'Overall risk (with load)', unit: '', max: 4, bands: [0, 1, 2, 3, 4] },
  wind_mph: { label: 'Wind', unit: 'mph', max: 60, bands: [0, 25, 35, 45, 55] },
  rain_in_hr: { label: 'Rain', unit: 'in/hr', max: 1.2, bands: [0, 0.1, 0.25, 0.5, 1.0] },
  snow_in_hr: { label: 'Snow', unit: 'in/hr', max: 3.6, bands: [0, 0.5, 1.0, 2.0, 3.0] },
}

// Risk level 0 still gets a little weight so a calm corridor shows up green.
export function heatWeight(metric: HeatMetric, value: number) {
  if (metric === 'risk') return (value + 1) / 5
  return Math.min(value / METRICS[metric].max, 1)
}

// Maps heatmap density (0 to 1) to colours. Each band switches colour right at its
// threshold so a 20 mph wind never reads as Moderate.
export function heatColorStops(metric: HeatMetric): (number | string)[] {
  const edges =
    metric === 'risk'
      ? [1, 2, 3, 4].map((k) => (k + 0.5) / 5)
      : METRICS[metric].bands.slice(1).map((b) => b / METRICS[metric].max)

  const stops: (number | string)[] = [0, 'rgba(0,0,0,0)', 0.03, 'rgba(47,158,91,0.25)']
  stops.push(Math.min(0.1, edges[0] - 0.02), LEVELS[0].color)
  edges.forEach((e, i) => {
    stops.push(e - 0.005, LEVELS[i].color, e, LEVELS[i + 1].color)
  })
  return stops
}
