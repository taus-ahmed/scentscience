import React, { useState } from 'react'
import { searchPerfumes } from '../api/client.js'
import { useNavigate } from 'react-router-dom'

const s = {
  page: { minHeight: '100vh', background: '#0a0a0f', padding: '2rem' },
  title: { fontSize: '1.8rem', fontWeight: 800, color: '#fff', marginBottom: '1.5rem' },
  inputRow: { display: 'flex', gap: '1rem', marginBottom: '2rem', flexWrap: 'wrap' },
  input: {
    flex: 1, minWidth: '200px', padding: '0.75rem 1rem',
    background: '#111827', border: '1px solid #374151', borderRadius: '8px',
    color: '#fff', fontSize: '0.95rem',
  },
  btn: {
    padding: '0.75rem 1.5rem', background: '#7c3aed', color: '#fff',
    border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600,
  },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' },
  card: {
    background: '#111827', border: '1px solid #1f2937', borderRadius: '12px',
    padding: '1.25rem', cursor: 'pointer', transition: 'border-color 0.2s',
  },
  cardName: { fontSize: '1.1rem', fontWeight: 700, color: '#fff', marginBottom: '0.25rem' },
  cardBrand: { color: '#a78bfa', fontSize: '0.85rem', marginBottom: '0.75rem' },
  badge: {
    display: 'inline-block', padding: '0.15rem 0.5rem',
    background: '#1f2937', borderRadius: '999px',
    fontSize: '0.7rem', color: '#94a3b8', marginRight: '0.3rem',
  },
  ratings: { display: 'flex', gap: '1rem', marginTop: '0.75rem' },
  ratingItem: { color: '#6b7280', fontSize: '0.75rem' },
  ratingVal: { color: '#e5e7eb', fontWeight: 700 },
  empty: { color: '#4b5563', textAlign: 'center', marginTop: '4rem', fontSize: '1rem' },
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
      setResults(data)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = e => {
    if (e.key === 'Enter') handleSearch()
  }

  return (
    <div style={s.page}>
      <h1 style={s.title}>Browse Perfumes</h1>
      <div style={s.inputRow}>
        <input
          style={s.input} placeholder="Search by name..." value={query}
          onChange={e => setQuery(e.target.value)} onKeyDown={handleKeyDown}
        />
        <input
          style={s.input} placeholder="Filter by brand..." value={brand}
          onChange={e => setBrand(e.target.value)} onKeyDown={handleKeyDown}
        />
        <button style={s.btn} onClick={handleSearch} disabled={loading}>
          {loading ? 'Searching…' : 'Search'}
        </button>
      </div>

      {results.length === 0 && !loading && (
        <p style={s.empty}>Search for a perfume above to browse the database.</p>
      )}

      <div style={s.grid}>
        {results.map(p => (
          <div
            key={p.id} style={s.card}
            onClick={() => navigate(`/?name=${encodeURIComponent(p.name)}&brand=${encodeURIComponent(p.brand)}`)}
            onMouseEnter={e => e.currentTarget.style.borderColor = '#4c1d95'}
            onMouseLeave={e => e.currentTarget.style.borderColor = '#1f2937'}
          >
            <div style={s.cardName}>{p.name}</div>
            <div style={s.cardBrand}>{p.brand} · {p.concentration}</div>
            <div>
              {(p.accords || []).slice(0, 3).map(a => (
                <span key={a} style={s.badge}>{a}</span>
              ))}
            </div>
            <div style={s.ratings}>
              <div style={s.ratingItem}>
                Longevity <span style={s.ratingVal}>{p.community_longevity_rating?.toFixed(1)}</span>
              </div>
              <div style={s.ratingItem}>
                Sillage <span style={s.ratingVal}>{p.community_sillage_rating?.toFixed(1)}</span>
              </div>
              <div style={s.ratingItem}>
                Overall <span style={s.ratingVal}>{p.community_overall_rating?.toFixed(1)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
