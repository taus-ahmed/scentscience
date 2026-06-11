import React, { useState, useEffect } from 'react'
import { searchPerfumes } from '../api/client.js'

const SKIN_TYPES = ['', 'dry', 'oily', 'combination']
const SEASONS = ['', 'spring', 'summer', 'fall', 'winter']
const TIMES = ['', 'morning', 'afternoon', 'evening', 'night']

const s = {
  wrapper: { maxWidth: '700px', margin: '0 auto' },
  mainRow: { display: 'flex', gap: '0.75rem', marginBottom: '0.75rem' },
  input: {
    flex: 1, padding: '0.875rem 1.25rem',
    background: '#111827', border: '1px solid #374151', borderRadius: '12px',
    color: '#fff', fontSize: '1rem', outline: 'none',
  },
  btn: {
    padding: '0.875rem 1.75rem', background: 'linear-gradient(135deg, #7c3aed, #4f46e5)',
    border: 'none', borderRadius: '12px', color: '#fff',
    fontWeight: 700, cursor: 'pointer', fontSize: '1rem', whiteSpace: 'nowrap',
  },
  contextRow: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' },
  select: {
    padding: '0.4rem 0.75rem', background: '#111827', border: '1px solid #374151',
    borderRadius: '8px', color: '#9ca3af', fontSize: '0.8rem', cursor: 'pointer',
  },
  suggestions: {
    position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
    background: '#1f2937', border: '1px solid #374151', borderRadius: '8px',
    overflow: 'hidden', marginTop: '4px',
  },
  suggestion: {
    padding: '0.75rem 1rem', cursor: 'pointer', borderBottom: '1px solid #374151',
    color: '#e5e7eb', fontSize: '0.9rem',
  },
}

export default function PerfumeSearch({ onSearch, loading }) {
  const [name, setName] = useState('')
  const [brand, setBrand] = useState('')
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

  const pickSuggestion = s => {
    setName(s.name)
    setBrand(s.brand)
    setShowSuggestions(false)
  }

  return (
    <div style={s.wrapper}>
      <div style={{ position: 'relative' }}>
        <div style={s.mainRow}>
          <input
            style={s.input} placeholder="Enter perfume name (e.g. Sauvage, Aventus…)"
            value={name} onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
            onFocus={() => suggestions.length && setShowSuggestions(true)}
          />
          <input
            style={{ ...s.input, flex: '0 0 160px' }} placeholder="Brand (optional)"
            value={brand} onChange={e => setBrand(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && submit()}
          />
          <button style={s.btn} onClick={submit} disabled={loading || !name}>
            {loading ? '…' : 'Predict'}
          </button>
        </div>

        {showSuggestions && suggestions.length > 0 && (
          <div style={s.suggestions}>
            {suggestions.map(sg => (
              <div key={sg.id} style={s.suggestion}
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

      <div style={s.contextRow}>
        <select style={s.select} value={skinType} onChange={e => setSkinType(e.target.value)}>
          <option value="">Skin type</option>
          {SKIN_TYPES.filter(Boolean).map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </select>
        <select style={s.select} value={season} onChange={e => setSeason(e.target.value)}>
          <option value="">Season</option>
          {SEASONS.filter(Boolean).map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </select>
        <select style={s.select} value={timeOfDay} onChange={e => setTimeOfDay(e.target.value)}>
          <option value="">Time of day</option>
          {TIMES.filter(Boolean).map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
        </select>
      </div>
    </div>
  )
}
