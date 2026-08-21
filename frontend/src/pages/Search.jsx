import React, { useState } from 'react'
import { searchPerfumes, getAllPerfumes } from '../api/client.js'
import { useNavigate } from 'react-router-dom'
import { BRANDS } from '../constants/brands.js'

const GOLD = '#C9A84C'
const CARD_BG = '#111827'
const BORDER_GOLD = 'rgba(201,168,76,0.25)'

const BADGE_STYLE = {
  display: 'inline-block', padding: '0.15rem 0.5rem',
  background: '#1f2937', borderRadius: '999px',
  fontSize: '0.7rem', color: '#94a3b8', marginRight: '0.3rem',
}

const GENDER_META = {
  masculine: { label: 'For Him', color: 'var(--gender-masculine)', bg: '#0D1520' },
  feminine: { label: 'For Her', color: 'var(--gender-feminine)', bg: '#1A0F16' },
  unisex: { label: 'For Him & Her', color: 'var(--gender-unisex)', bg: '#150F1A' },
}

function GenderBadge({ genderVote }) {
  const meta = GENDER_META[genderVote]
  if (!meta) return null
  return (
    <span
      style={{
        display: 'inline-block', padding: '0.1rem 0.5rem', borderRadius: '999px',
        fontSize: '0.65rem', fontWeight: 700, color: meta.color,
        background: meta.bg,
        border: `1px solid color-mix(in srgb, ${meta.color} 40%, transparent)`,
      }}
    >
      {meta.label}
    </span>
  )
}

function accordIntersects(arr, keywords) {
  if (!arr || arr.length === 0) return false
  const lower = arr.map(a => a.toLowerCase())
  return keywords.some(kw => lower.some(a => a.includes(kw)))
}

const VIBES = [
  {
    id: 'fresh', emoji: '🌊', title: 'Fresh & Clean', sub: 'Light, airy, office-ready',
    filter: p => accordIntersects(p.accords, ['aquatic', 'citrus', 'fresh', 'green', 'ozonic', 'marine']),
  },
  {
    id: 'sexy', emoji: '🔥', title: 'Sexy & Seductive', sub: 'Dark, magnetic, date nights',
    filter: p => accordIntersects(p.accords, ['amber', 'oriental', 'animalic', 'smoky', 'oud', 'dark spicy']),
  },
  {
    id: 'gateway', emoji: '🚪', title: 'Gateway', sub: 'Safe bets for fragrance newcomers',
    filter: p => (p.community_overall_rating || 0) >= 4.0 && (p.community_sillage_rating || 5) <= 3.5,
  },
  {
    id: 'office', emoji: '💼', title: 'Office Ready', sub: 'Professional, subtle projection',
    filter: p => (p.community_sillage_rating || 5) <= 3.0 && accordIntersects(p.accords, ['citrus', 'woody', 'powdery', 'aromatic', 'clean']),
  },
  {
    id: 'date', emoji: '🌙', title: 'Date Night', sub: 'Memorable, intimate evenings',
    filter: p => accordIntersects(p.accords, ['floral', 'amber', 'oriental', 'musk']) && (p.community_overall_rating || 0) >= 3.8,
  },
  {
    id: 'winter', emoji: '❄️', title: 'Winter Warmers', sub: 'Rich, cozy, cold weather staples',
    filter: p => accordIntersects(p.accords, ['amber', 'vanilla', 'woody', 'smoky', 'spicy', 'oriental', 'balsamic']),
  },
  {
    id: 'summer', emoji: '☀️', title: 'Summer Staples', sub: 'Fresh, light, heat-proof',
    filter: p => accordIntersects(p.accords, ['citrus', 'aquatic', 'fresh', 'fruity', 'green', 'ozonic']),
  },
  {
    id: 'performers', emoji: '🏆', title: 'Best Performers', sub: 'Highest longevity + sillage scores',
    filter: p => (p.community_longevity_rating || 0) >= 3.8 && (p.community_sillage_rating || 0) >= 3.8,
  },
  {
    id: 'value', emoji: '💰', title: 'Best Value', sub: 'High scores, lower price range',
    filter: p => (p.community_overall_rating || 0) >= 4.2,
  },
]

function PerfumeCard({ p, onClick }) {
  return (
    <div
      onClick={() => onClick(p)}
      style={{
        background: CARD_BG, border: '1px solid #1f2937',
        borderRadius: '12px', cursor: 'pointer', padding: '1rem 1.25rem',
        transition: 'border-color 0.2s',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = '#4c1d95' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = '#1f2937' }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.2rem' }}>
        <span style={{ fontWeight: 700, color: '#fff' }}>{p.name}</span>
        <GenderBadge genderVote={p.gender_vote} />
      </div>
      <div style={{ fontSize: '0.85rem', color: '#a78bfa', marginBottom: '0.6rem' }}>
        {p.brand}{p.concentration ? ` · ${p.concentration}` : ''}
      </div>
      <div style={{ marginBottom: '0.6rem' }}>
        {(p.accords || []).slice(0, 3).map(a => (
          <span key={a} style={BADGE_STYLE}>{a}</span>
        ))}
      </div>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <span style={{ fontSize: '0.72rem', color: '#6b7280' }}>
          Longevity <strong style={{ color: '#e5e7eb' }}>{(p.longevity_hours ?? p.community_longevity_rating)?.toFixed(1) ?? '—'}</strong>
        </span>
        <span style={{ fontSize: '0.72rem', color: '#6b7280' }}>
          Sillage <strong style={{ color: '#e5e7eb' }}>{p.community_sillage_rating?.toFixed(1) ?? '—'}</strong>
        </span>
        <span style={{ fontSize: '0.72rem', color: '#6b7280' }}>
          Overall <strong style={{ color: '#e5e7eb' }}>{p.community_overall_rating?.toFixed(1) ?? '—'}</strong>
        </span>
      </div>
    </div>
  )
}

function ResultsGrid({ results, loading, onCardClick, emptyMsg }) {
  if (loading) {
    return <p style={{ textAlign: 'center', color: '#6b7280', padding: '3rem 0' }}>Loading…</p>
  }
  if (!results.length && emptyMsg) {
    return <p style={{ textAlign: 'center', color: '#4b5563', padding: '3rem 0', fontSize: '0.9rem' }}>{emptyMsg}</p>
  }
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.75rem' }}>
      {results.map(p => <PerfumeCard key={p.id} p={p} onClick={onCardClick} />)}
    </div>
  )
}

export default function Search() {
  const [tab, setTab] = useState(0)
  const navigate = useNavigate()

  // Tab 1 — Search
  const [query, setQuery] = useState('')
  const [brandQ, setBrandQ] = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  // Tab 2 — By Brand
  const [activeBrand, setActiveBrand] = useState(null)
  const [brandResults, setBrandResults] = useState([])
  const [brandLoading, setBrandLoading] = useState(false)

  // Tab 3 — By Vibe
  const [activeVibe, setActiveVibe] = useState(null)
  const [vibeResults, setVibeResults] = useState([])
  const [vibeLoading, setVibeLoading] = useState(false)

  const goToPerfume = p =>
    navigate(`/?name=${encodeURIComponent(p.name)}&brand=${encodeURIComponent(p.brand)}`)

  const handleSearch = async () => {
    if (!query && !brandQ) return
    setSearchLoading(true)
    setSearched(true)
    try {
      const data = await searchPerfumes(query, brandQ)
      setSearchResults(data || [])
    } finally {
      setSearchLoading(false)
    }
  }

  const handleBrandClick = async brand => {
    setActiveBrand(brand)
    setBrandLoading(true)
    setBrandResults([])
    try {
      const data = await searchPerfumes('', brand)
      setBrandResults(data || [])
    } finally {
      setBrandLoading(false)
    }
  }

  const handleVibeClick = async vibe => {
    if (activeVibe === vibe.id) return
    setActiveVibe(vibe.id)
    setVibeLoading(true)
    setVibeResults([])
    try {
      const data = await getAllPerfumes(200)
      setVibeResults((data || []).filter(vibe.filter).slice(0, 50))
    } finally {
      setVibeLoading(false)
    }
  }

  const activeVibeObj = VIBES.find(v => v.id === activeVibe)

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0f', padding: '1.5rem 1.5rem 4rem' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 900, color: '#fff', marginBottom: '1.5rem' }}>
        Browse Perfumes
      </h1>

      {/* Tab bar */}
      <div style={{ borderBottom: '1px solid #1f2937', marginBottom: '2rem', display: 'flex' }}>
        {['Search', 'By Brand', 'By Vibe'].map((label, i) => (
          <button
            key={i}
            onClick={() => setTab(i)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              borderBottom: `2px solid ${tab === i ? GOLD : 'transparent'}`,
              color: tab === i ? GOLD : '#6b7280',
              fontWeight: tab === i ? 700 : 400,
              fontSize: '0.95rem', padding: '0.65rem 1.5rem',
              marginBottom: '-1px', transition: 'color 0.2s',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* ── Tab 1: Search ── */}
      {tab === 0 && (
        <div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '1.5rem' }}>
            <input
              style={{
                flex: '1 1 200px', background: CARD_BG, border: '1px solid #374151',
                borderRadius: '8px', color: '#fff', fontSize: '0.95rem',
                padding: '0.7rem 1rem', outline: 'none',
              }}
              placeholder="Search by name…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <input
              style={{
                flex: '0 1 180px', background: CARD_BG, border: '1px solid #374151',
                borderRadius: '8px', color: '#fff', fontSize: '0.95rem',
                padding: '0.7rem 1rem', outline: 'none',
              }}
              placeholder="Filter by brand…"
              value={brandQ}
              onChange={e => setBrandQ(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={searchLoading}
              style={{
                background: '#7c3aed', color: '#fff', border: 'none',
                borderRadius: '8px', cursor: 'pointer', fontWeight: 600,
                fontSize: '0.95rem', padding: '0.7rem 1.5rem',
                opacity: searchLoading ? 0.7 : 1,
              }}
            >
              {searchLoading ? 'Searching…' : 'Search'}
            </button>
          </div>
          <ResultsGrid
            results={searchResults}
            loading={searchLoading}
            onCardClick={goToPerfume}
            emptyMsg={searched ? 'No results found.' : 'Search for a perfume above to browse the database.'}
          />
        </div>
      )}

      {/* ── Tab 2: By Brand ── */}
      {tab === 1 && (
        <div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
            gap: '0.6rem',
            marginBottom: '2rem',
          }}>
            {BRANDS.map(brand => {
              const isActive = activeBrand === brand
              return (
                <div
                  key={brand}
                  onClick={() => handleBrandClick(brand)}
                  style={{
                    background: isActive ? 'rgba(201,168,76,0.1)' : CARD_BG,
                    border: `1px solid ${isActive ? GOLD : BORDER_GOLD}`,
                    borderRadius: '10px', padding: '0.6rem 0.75rem',
                    cursor: 'pointer', textAlign: 'center',
                    fontSize: '0.78rem', fontWeight: isActive ? 700 : 500,
                    color: isActive ? GOLD : '#d1d5db',
                    transition: 'all 0.18s',
                    boxShadow: isActive ? `0 0 14px rgba(201,168,76,0.2)` : 'none',
                    lineHeight: 1.3,
                  }}
                  onMouseEnter={e => { if (!isActive) e.currentTarget.style.boxShadow = '0 0 10px rgba(201,168,76,0.15)' }}
                  onMouseLeave={e => { if (!isActive) e.currentTarget.style.boxShadow = 'none' }}
                >
                  {brand}
                </div>
              )
            })}
          </div>

          {activeBrand ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '1rem' }}>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: GOLD, margin: 0 }}>
                  {activeBrand}
                </h2>
                {!brandLoading && (
                  <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                    {brandResults.length} result{brandResults.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
              <ResultsGrid
                results={brandResults}
                loading={brandLoading}
                onCardClick={goToPerfume}
                emptyMsg="No results found for this brand."
              />
            </>
          ) : (
            <p style={{ textAlign: 'center', color: '#4b5563', padding: '3rem 0', fontSize: '0.9rem' }}>
              Select a brand above to browse its perfumes.
            </p>
          )}
        </div>
      )}

      {/* ── Tab 3: By Vibe ── */}
      {tab === 2 && (
        <div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: '0.9rem',
            marginBottom: '2.5rem',
          }}>
            {VIBES.map(vibe => {
              const isActive = activeVibe === vibe.id
              return (
                <div
                  key={vibe.id}
                  onClick={() => handleVibeClick(vibe)}
                  style={{
                    background: isActive ? 'rgba(201,168,76,0.08)' : 'linear-gradient(135deg, #111827 0%, #0d1117 100%)',
                    border: `1px solid ${isActive ? GOLD : BORDER_GOLD}`,
                    borderRadius: '14px', padding: '1.2rem 1.1rem',
                    cursor: 'pointer', textAlign: 'left',
                    transition: 'all 0.18s',
                    boxShadow: isActive ? `0 0 18px rgba(201,168,76,0.18)` : 'none',
                  }}
                  onMouseEnter={e => { if (!isActive) e.currentTarget.style.boxShadow = '0 0 12px rgba(201,168,76,0.1)' }}
                  onMouseLeave={e => { if (!isActive) e.currentTarget.style.boxShadow = 'none' }}
                >
                  <div style={{ fontSize: '1.75rem', marginBottom: '0.45rem', lineHeight: 1 }}>
                    {vibe.emoji}
                  </div>
                  <div style={{ fontWeight: 700, fontSize: '0.9rem', marginBottom: '0.25rem', color: isActive ? GOLD : '#e5e7eb' }}>
                    {vibe.title}
                  </div>
                  <div style={{ fontSize: '0.73rem', color: '#6b7280', lineHeight: 1.4 }}>
                    {vibe.sub}
                  </div>
                </div>
              )
            })}
          </div>

          {activeVibeObj ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '1rem' }}>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: GOLD, margin: 0 }}>
                  {activeVibeObj.emoji} {activeVibeObj.title}
                </h2>
                {!vibeLoading && (
                  <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>
                    {vibeResults.length} result{vibeResults.length !== 1 ? 's' : ''} (top 50)
                  </span>
                )}
              </div>
              <ResultsGrid
                results={vibeResults}
                loading={vibeLoading}
                onCardClick={goToPerfume}
                emptyMsg="No perfumes matched this vibe in the current sample."
              />
            </>
          ) : (
            <p style={{ textAlign: 'center', color: '#4b5563', padding: '1rem 0', fontSize: '0.9rem' }}>
              Select a vibe above to find matching perfumes.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
