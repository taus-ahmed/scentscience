import React, { useState, useEffect, useRef } from 'react'
import { searchPerfumes } from '../api/client.js'
import { splitBrandPrefix } from '../constants/brands.js'

const SEASON_OPTS  = ['spring', 'summer', 'fall', 'winter']
const TIME_OPTS    = ['morning', 'afternoon', 'evening', 'night']
const SKIN_OPTS    = ['dry', 'normal', 'oily', 'combo']

const INPUT_STYLE = {
  background: '#111729', border: '1px solid rgba(201,168,76,0.2)', borderRadius: '12px',
  color: '#E8DCC8', fontSize: '1rem', outline: 'none',
}
const BTN_STYLE = {
  background: 'linear-gradient(135deg, #8B6914, #C9A84C)',
  border: 'none', borderRadius: '12px', color: '#0B0F1A',
  fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap',
}
const SUGGESTIONS_STYLE = {
  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
  background: '#141A2E', border: '1px solid rgba(201,168,76,0.2)', borderRadius: '8px',
  maxHeight: '320px', overflowY: 'auto', marginTop: '4px',
}

function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1) }

function PillGroup({ label, options, value, onChange }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-xs pt-1 shrink-0 w-12" style={{ color: '#4A4235' }}>{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {options.map(opt => {
          const active = value === opt
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onChange(active ? '' : opt)}
              className="px-2.5 py-1 rounded-full text-xs transition-all"
              style={{
                background: active ? 'rgba(201,168,76,0.12)' : '#111729',
                border: `1px solid ${active ? '#C9A84C' : 'rgba(201,168,76,0.12)'}`,
                color: active ? '#E8DCC8' : '#5A5245',
                cursor: 'pointer',
                fontWeight: active ? 600 : 400,
              }}
            >
              {cap(opt)}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function PerfumeSearch({ onSearch, loading, defaultName = '', defaultBrand = '' }) {
  const [name, setName] = useState(defaultName)
  const [brand, setBrand] = useState(defaultBrand)
  const [skinType, setSkinType] = useState('')
  const [season, setSeason] = useState('')
  const [timeOfDay, setTimeOfDay] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)

  const containerRef = useRef(null)
  const skipNextFetchRef = useRef(false)
  const abortRef = useRef(null)
  const cacheRef = useRef(new Map())

  // Closes the dropdown on any click outside the input/suggestions area —
  // a defensive backstop independent of the debounce/pick race below.
  useEffect(() => {
    const handleOutsideClick = e => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  useEffect(() => {
    // pickSuggestion sets `name` too — skip the fetch that would otherwise
    // reopen the dropdown right after a selection was made.
    if (skipNextFetchRef.current) {
      skipNextFetchRef.current = false
      return
    }
    if (name.length < 2) { setSuggestions([]); return }

    const cacheKey = name.trim().toLowerCase()
    const cached = cacheRef.current.get(cacheKey)
    if (cached) {
      setSuggestions(cached)
      setShowSuggestions(true)
      return
    }

    const timer = setTimeout(async () => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      try {
        const results = await searchPerfumes(name, undefined, controller.signal)
        const top = results.slice(0, 6)
        cacheRef.current.set(cacheKey, top)
        setSuggestions(top)
        setShowSuggestions(true)
      } catch { /* ignore — includes aborted/superseded requests */ }
    }, 150)
    return () => clearTimeout(timer)
  }, [name])

  const submit = () => {
    setShowSuggestions(false)

    // If the user typed "Brand Name" fully into the Name field and left
    // Brand empty, split it so the search (and the UI) reflect both fields.
    let finalName = name
    let finalBrand = brand
    if (!brand.trim()) {
      const split = splitBrandPrefix(name)
      if (split) {
        finalName = split.name
        finalBrand = split.brand
        setName(split.name)
        setBrand(split.brand)
      }
    }

    const context = {}
    if (skinType) context.skin_type = skinType === 'combo' ? 'combination' : skinType
    if (season) context.season = season
    if (timeOfDay) context.time_of_day = timeOfDay
    onSearch({ name: finalName, brand: finalBrand, context: Object.keys(context).length ? context : null })
  }

  const pickSuggestion = sg => {
    skipNextFetchRef.current = true
    setSuggestions([])
    setShowSuggestions(false)
    setName(sg.name)
    setBrand(sg.brand)
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-2 sm:px-0">
      <div className="relative mb-3" ref={containerRef}>
        {/* Search row */}
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
          <input
            style={INPUT_STYLE}
            className="w-full sm:flex-1 px-4 py-3 sm:py-3.5 text-sm sm:text-base"
            placeholder="Enter perfume name (e.g. Sauvage, Aventus…)"
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            onFocus={() => suggestions.length && setShowSuggestions(true)}
          />
          <div className="flex gap-2">
            <input
              style={INPUT_STYLE}
              className="flex-1 sm:w-36 sm:flex-none px-4 py-3 sm:py-3.5 text-sm sm:text-base"
              placeholder="Brand"
              value={brand}
              onChange={e => setBrand(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && submit()}
            />
            <button
              style={BTN_STYLE}
              className="px-5 py-3 sm:px-6 sm:py-3.5 text-sm sm:text-base rounded-xl"
              onClick={submit}
              disabled={loading || !name}
            >
              {loading ? '…' : 'Predict'}
            </button>
          </div>
        </div>

        {showSuggestions && suggestions.length > 0 && (
          <div style={SUGGESTIONS_STYLE}>
            {suggestions.map(sg => (
              <div
                key={sg.id}
                className="px-4 py-3 cursor-pointer border-b text-sm"
                style={{ borderColor: 'rgba(201,168,76,0.10)', color: '#E8DCC8' }}
                onClick={() => pickSuggestion(sg)}
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(201,168,76,0.06)'}
                onMouseLeave={e => e.currentTarget.style.background = ''}
              >
                <strong>{sg.name}</strong>
                <span style={{ color: '#C9A84C', marginLeft: '0.5rem' }}>{sg.brand}</span>
                <span style={{ color: '#5A5245', marginLeft: '0.5rem', fontSize: '0.78rem' }}>
                  {sg.concentration}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Context selectors — pill groups */}
      <div className="flex flex-col gap-2 text-left">
        <PillGroup label="Season" options={SEASON_OPTS} value={season} onChange={setSeason} />
        <PillGroup label="Time"   options={TIME_OPTS}   value={timeOfDay} onChange={setTimeOfDay} />
        <PillGroup label="Skin"   options={SKIN_OPTS}   value={skinType} onChange={setSkinType} />
      </div>
    </div>
  )
}
