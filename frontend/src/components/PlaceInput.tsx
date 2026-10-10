import { useEffect, useId, useRef, useState } from 'react'
import { geocode } from '../api'
import type { Place, ResolvedPlace } from '../types'

interface Props {
  label: string
  value: Place
  onChange: (p: Place) => void
  placeholder?: string
}

export default function PlaceInput({ label, value, onChange, placeholder }: Props) {
  const id = useId()
  const [suggestions, setSuggestions] = useState<ResolvedPlace[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const picked = useRef(false)

  useEffect(() => {
    const q = value.label.trim()
    if (picked.current || q.length < 3) {
      picked.current = false
      setSuggestions([])
      return
    }
    const ctrl = new AbortController()
    const t = setTimeout(() => {
      geocode(q, ctrl.signal)
        .then((r) => {
          setSuggestions(r)
          setActive(-1)
        })
        .catch(() => {})
    }, 250)
    return () => {
      clearTimeout(t)
      ctrl.abort()
    }
  }, [value.label])

  function choose(p: ResolvedPlace) {
    picked.current = true
    onChange(p)
    setOpen(false)
    setSuggestions([])
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || !suggestions.length) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => (a + 1) % suggestions.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => (a <= 0 ? suggestions.length - 1 : a - 1))
    } else if (e.key === 'Enter' && active >= 0) {
      e.preventDefault()
      choose(suggestions[active])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const showList = open && suggestions.length > 0

  return (
    <div className="field place-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        autoComplete="off"
        role="combobox"
        aria-expanded={showList}
        aria-controls={`${id}-list`}
        placeholder={placeholder}
        value={value.label}
        onChange={(e) => {
          onChange({ label: e.target.value, lat: null, lon: null })
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
      />
      {value.lat != null && <span className="pin-ok" title="Location confirmed">&#10003;</span>}
      {showList && (
        <ul id={`${id}-list`} className="suggestions" role="listbox">
          {suggestions.map((s, i) => (
            <li
              key={`${s.lat},${s.lon}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'active' : ''}
              onMouseDown={(e) => {
                e.preventDefault()
                choose(s)
              }}
            >
              {s.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
