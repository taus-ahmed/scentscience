import React, { useState, useEffect } from 'react'
import { searchPerfumes } from '../api/client.js'

const SEASON_OPTS  = ['spring', 'summer', 'fall', 'winter']
const TIME_OPTS    = ['morning', 'afternoon', 'evening', 'night']
const SKIN_OPTS    = ['dry', 'normal', 'oily', 'combo']

const INPUT_STYLE = {
  background: '#111827', border: '1px solid #374151', borderRadius: '12px',
  color: '#fff', fontSize: '1rem', outline: 'none',
}
const BTN_STYLE = {
  background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
  border: 'none', borderRadius: '12px', color: '#fff',
  fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap',
}
const SUGGESTIONS_STYLE = {
  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
  background: '#1f2937', border: '1px solid #374151', borderRadius: '8px',
  overflow: 'hidden', marginTop: '4px',
}

function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1) }

function PillGroup({ label, options, value, onChange }) {
  return (
    <div className="flex items-start gap-2">
      <span className="text-xs pt-1 shrink-0 w-12" style={{ color: '#4b5563' }}>{label}</span>
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
                background: active ? '#4338ca' : '#111827',
                border: `1px solid ${active ? '#6366f1' : '#374151'}`,
                color: active ? '#e0e7ff' : '#6b7280',
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

  useEffect(() => {
    if (name.length < 2) { setSuggestions([]); return }
    const timer = setTimeout(async () => {
      try {
        const results = await searchPerfumes(name)
        setSuggestions(results.slice(0, 6))
        setShowSuggestions(true)
      } catch { /* ignore */ }
    }, 300)
    return () => clearTimeout(timer)
  }, [name])

  const submit = () => {
    setShowSuggestions(false)
    const context = {}
    if (skinType) context.skin_type = skinType === 'combo' ? 'combination' : skinType
    if (season) context.season = season
    if (timeOfDay) context.time_of_day = timeOfDay
    onSearch({ name, brand, context: Object.keys(context).length ? context : null })
  }

  const pickSuggestion = sg => {
    setName(sg.name)
    setBrand(sg.brand)
    setShowSuggestions(false)
  }

  return (
    <div className="w-full max-w-2xl mx-auto px-2 sm:px-0">
      <div className="relative mb-3">
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
                style={{ borderColor: '#374151', color: '#e5e7eb' }}
                onClick={() => pickSuggestion(sg)}
                onMouseEnter={e => e.currentTarget.style.background = '#374151'}
                onMouseLeave={e => e.currentTarget.style.background = ''}
              >
                <strong>{sg.name}</strong>
                <span style={{ color: '#a78bfa', marginLeft: '0.5rem' }}>{sg.brand}</span>
                <span style={{ color: '#6b7280', marginLeft: '0.5rem', fontSize: '0.78rem' }}>
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
