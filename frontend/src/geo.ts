import type { Route } from './types'

type LonLat = [number, number]

const R = 3958.8 // earth radius, miles

function haversineMi([lon1, lat1]: LonLat, [lon2, lat2]: LonLat) {
  const toRad = Math.PI / 180
  const dLat = (lat2 - lat1) * toRad
  const dLon = (lon2 - lon1) * toRad
  const a =
    Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) * Math.sin(dLon / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(a))
}

export function cumulativeMiles(line: LonLat[]) {
  const out = [0]
  for (let i = 1; i < line.length; i++) out.push(out[i - 1] + haversineMi(line[i - 1], line[i]))
  return out
}

export function pointAtFraction(line: LonLat[], cum: number[], fraction: number): LonLat {
  const target = Math.max(0, Math.min(1, fraction)) * cum[cum.length - 1]
  let lo = 0
  let hi = cum.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (cum[mid] <= target) lo = mid
    else hi = mid
  }
  const span = cum[hi] - cum[lo]
  const t = span ? (target - cum[lo]) / span : 0
  return [
    line[lo][0] + (line[hi][0] - line[lo][0]) * t,
    line[lo][1] + (line[hi][1] - line[lo][1]) * t,
  ]
}

// Where the truck is on this route at time `ms`, based on the checkpoint ETAs.
export function truckPosition(route: Route, cum: number[], ms: number) {
  const cps = route.checkpoints
  const times = cps.map((c) => Date.parse(c.eta))
  if (ms <= times[0]) return { pos: route.geometry[0], state: 'waiting' as const }
  if (ms >= times[times.length - 1]) {
    return { pos: route.geometry[route.geometry.length - 1], state: 'arrived' as const }
  }
  let i = 0
  while (times[i + 1] < ms) i++
  const t = (ms - times[i]) / (times[i + 1] - times[i])
  const mile = cps[i].mile + (cps[i + 1].mile - cps[i].mile) * t
  return {
    pos: pointAtFraction(route.geometry, cum, mile / route.distance_miles),
    state: 'driving' as const,
  }
}

export function downsample(line: LonLat[], maxPoints: number) {
  if (line.length <= maxPoints) return line
  const step = (line.length - 1) / (maxPoints - 1)
  return Array.from({ length: maxPoints }, (_, i) => line[Math.round(i * step)])
}
