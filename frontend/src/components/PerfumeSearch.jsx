import React, { useState, useEffect } from 'react'
import { searchPerfumes } from '../api/client.js'

const SKIN_TYPES = ['', 'dry', 'oily', 'combination']
const SEASONS = ['', 'spring', 'summer', 'fall', 'winter']
const TIMES = ['', 'morning', 'afternoon', 'evening', 'night']

const INPUT_STYLE = {
  background: '#111827', border: '1px solid #374151', borderRadius: '12px',
  color: '#fff', fontSize: '1rem', outline: 'none',
}
const BTN_STYLE = {
  background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
  border: 'none', borderRadius: '12px', color: '#fff',
  fontWeight: 700, cursor: 'pointer', whiteSpace: 'nowrap',
}
const SELECT_STYLE = {
  background: '#111827', border: '1px solid #374151',
  borderRadius: '8px', color: '#9ca3af', cursor: 'pointer',
}
const SUGGESTIONS_STYLE = {
  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
  background: '#1f2937', border: '1px solid #374151', borderRadius: '8px',
  overflow: 'hidden', marginTop: '4px',
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
    if (skinType) context.skin_type = skinType
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
      <div className="relative">
        {/* Main input row — stacks on mobile, side-by-side on sm+ */}
        <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 mb-2 sm:mb-3">
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
                <span style={{ color: '#6b7280', marginLeft: '0.5rem', fontSize: '0.78rem' }}>{sg.concentration}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Context selectors */}
      <div className="flex flex-wrap gap-2">
        <select style={SELECT_STYLE} className="flex-1 min-w-[110px] px-2 py-1.5 text-xs sm:text-sm" value={skinType} onChange={e => setSkinType(e.target.value)}>
          <option value="">Skin type</option>
          {SKIN_TYPES.filter(Boolean).map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </select>
        <select style={SELECT_STYLE} className="flex-1 min-w-[100px] px-2 py-1.5 text-xs sm:text-sm" value={season} onChange={e => setSeason(e.target.value)}>
          <option value="">Season</option>
          {SEASONS.filter(Boolean).map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </select>
        <select style={SELECT_STYLE} className="flex-1 min-w-[110px] px-2 py-1.5 text-xs sm:text-sm" value={timeOfDay} onChange={e => setTimeOfDay(e.target.value)}>
          <option value="">Time of day</option>
          {TIMES.filter(Boolean).map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </select>
      </div>
    </div>
  )
}
