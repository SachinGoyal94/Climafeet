export type RiskLabel = 'Low' | 'Moderate' | 'High' | 'Severe' | 'No Travel'

export interface Place {
  label: string
  lat?: number | null
  lon?: number | null
}

export interface ResolvedPlace {
  label: string
  lat: number
  lon: number
}

export interface Weather {
  wind_mph: number
  gust_mph: number
  rain_in_hr: number
  snow_in_hr: number
  temp_f: number
}

export interface Checkpoint {
  mile: number
  lat: number
  lon: number
  eta: string
  segment_miles: number
  weather: Weather
  level: number
  label: RiskLabel
  reasons: string[]
}

export interface RouteSummary {
  miles: Record<RiskLabel, number>
  avg_risk: number
  max_level: number
  max_label: RiskLabel
}

export interface Route {
  id: string
  name: string
  distance_miles: number
  duration_s: number
  traffic_delay_s: number
  departure: string
  arrival: string
  geometry: [number, number][]
  summary: RouteSummary
  checkpoints: Checkpoint[]
  rank: number
  recommended: boolean
}

export interface Recommendation {
  best_id: string
  ranking: string[]
  reason: string
  warning: string | null
}

export interface Plan {
  origin: ResolvedPlace
  destination: ResolvedPlace
  departure: string
  load_lb: number
  interval_miles: number
  bbox: [number, number, number, number]
  routes: Route[]
  recommendation: Recommendation
}

export interface PlanRequest {
  origin: Place
  destination: Place
  departure: string
  load_lb: number
  interval_miles: 10 | 25 | 50
}

export interface Heatmap {
  start: string
  hours: number
  step_deg: number
  cells: [number, number][]
  risk: number[][]
  wind_mph: number[][]
  rain_in_hr: number[][]
  snow_in_hr: number[][]
}

export type HeatMetric = 'risk' | 'wind_mph' | 'rain_in_hr' | 'snow_in_hr'
