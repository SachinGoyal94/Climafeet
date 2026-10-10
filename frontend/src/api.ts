import type { Heatmap, Plan, PlanRequest, ResolvedPlace } from './types'

const BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

export class ApiError extends Error {}

// DRF validation errors come back as nested {field: [messages]} objects
function flattenErrors(body: unknown, prefix = ''): string[] {
  if (typeof body === 'string') return [prefix ? `${prefix}: ${body}` : body]
  if (Array.isArray(body)) return body.flatMap((b) => flattenErrors(b, prefix))
  if (body && typeof body === 'object') {
    return Object.entries(body).flatMap(([k, v]) => {
      const key = k === 'detail' || k === 'non_field_errors' ? prefix : k.replace(/_/g, ' ')
      return flattenErrors(v, key)
    })
  }
  return []
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    })
  } catch (err) {
    if ((err as Error).name === 'AbortError') throw err
    throw new ApiError('Could not reach the server. Check your connection and try again.')
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`
    try {
      const msgs = flattenErrors(await res.json())
      if (msgs.length) message = msgs.join(' ')
    } catch {
      // body was not JSON, keep the generic message
    }
    throw new ApiError(message)
  }
  return res.json() as Promise<T>
}

export function geocode(q: string, signal?: AbortSignal) {
  return request<{ results: ResolvedPlace[] }>(`/api/geocode?q=${encodeURIComponent(q)}`, {
    signal,
  }).then((r) => r.results)
}

export function planTrip(body: PlanRequest) {
  return request<Plan>('/api/trips/plan', { method: 'POST', body: JSON.stringify(body) })
}

export function fetchHeatmap(
  body: { lines: [number, number][][]; start: string; load_lb: number },
  signal?: AbortSignal,
) {
  return request<Heatmap>('/api/heatmap', { method: 'POST', body: JSON.stringify(body), signal })
}
