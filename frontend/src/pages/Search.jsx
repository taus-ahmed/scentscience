import React, { useState } from 'react'
import { searchPerfumes } from '../api/client.js'
import { useNavigate } from 'react-router-dom'

const INPUT_STYLE = {
  background: '#111827', border: '1px solid #374151', borderRadius: '8px',
  color: '#fff', fontSize: '0.95rem',
}
const BTN_STYLE = {
  background: '#7c3aed', color: '#fff',
  border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600,
}
const CARD_STYLE = {
  background: '#111827', border: '1px solid #1f2937', borderRadius: '12px', cursor: 'pointer',
  transition: 'border-color 0.2s',
}
const BADGE_STYLE = {
  display: 'inline-block', padding: '0.15rem 0.5rem',
  background: '#1f2937', borderRadius: '999px',
  fontSize: '0.7rem', color: '#94a3b8', marginRight: '0.3rem',
}

export default function Search() {
  const [query, setQuery] = useState('')
  const [brand, setBrand] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSearch = async () => {
    if (!query && !brand) return
    setLoading(true)
    try {
      const data = await searchPerfumes(query, brand)
      setResults(data || [])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = e => {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <div className="min-h-screen px-4 py-6 sm:px-6 sm:py-8 md:px-8" style={{ background: '#0a0a0f' }}>
      <h1 className="text-2xl sm:text-3xl font-black text-white mb-4 sm:mb-6">Browse Perfumes</h1>

      {/* Search inputs — stacked on mobile, row on sm+ */}
      <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 mb-6 sm:mb-8">
        <input
          style={INPUT_STYLE}
          className="w-full sm:flex-1 px-3 py-2.5 sm:px-4 sm:py-3"
          placeholder="Search by name…"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <input
          style={INPUT_STYLE}
          className="w-full sm:w-48 px-3 py-2.5 sm:px-4 sm:py-3"
          placeholder="Filter by brand…"
          value={brand}
          onChange={e => setBrand(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          style={BTN_STYLE}
          className="w-full sm:w-auto px-5 py-2.5 sm:px-6 sm:py-3 text-sm sm:text-base"
          onClick={handleSearch}
          disabled={loading}
        >
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {results.length === 0 && !loading && (
        <p className="text-center mt-12 sm:mt-16 text-sm sm:text-base" style={{ color: '#4b5563' }}>
          Search for a perfume above to browse the database.
        </p>
      )}

      {/* Results grid — 1 col on mobile, 2 on sm, 3 on lg */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4">
        {results.map(p => (
          <div
            key={p.id}
            style={CARD_STYLE}
            className="p-4 sm:p-5"
            onClick={() => navigate(`/?name=${encodeURIComponent(p.name)}&brand=${encodeURIComponent(p.brand)}`)}
            onMouseEnter={e => e.currentTarget.style.borderColor = '#4c1d95'}
            onMouseLeave={e => e.currentTarget.style.borderColor = '#1f2937'}
          >
            <div className="text-base sm:text-lg font-bold text-white mb-1">{p.name}</div>
            <div className="text-sm mb-2 sm:mb-3" style={{ color: '#a78bfa' }}>
              {p.brand} · {p.concentration}
            </div>
            <div className="mb-2 sm:mb-3">
              {(p.accords || []).slice(0, 3).map(a => (
                <span key={a} style={BADGE_STYLE}>{a}</span>
              ))}
            </div>
            <div className="flex gap-3 sm:gap-4">
              <div className="text-xs" style={{ color: '#6b7280' }}>
                Longevity <span className="font-bold" style={{ color: '#e5e7eb' }}>{p.community_longevity_rating?.toFixed(1)}</span>
              </div>
              <div className="text-xs" style={{ color: '#6b7280' }}>
                Sillage <span className="font-bold" style={{ color: '#e5e7eb' }}>{p.community_sillage_rating?.toFixed(1)}</span>
              </div>
              <div className="text-xs" style={{ color: '#6b7280' }}>
                Overall <span className="font-bold" style={{ color: '#e5e7eb' }}>{p.community_overall_rating?.toFixed(1)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
