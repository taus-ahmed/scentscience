import React, { useState, useEffect } from 'react'
import { searchPerfumes, browsePerfumes, listBrands } from '../api/client.js'
import { useNavigate } from 'react-router-dom'
import { displayConcentration } from '../utils/concentration.js'

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
  feminine:  { label: 'For Her', color: 'var(--gender-feminine)',  bg: '#1A0F16' },
  unisex:    { label: 'Unisex',  color: 'var(--gender-unisex)',    bg: '#150F1A' },
}

function GenderBadge({ genderVote }) {
  const meta = GENDER_META[genderVote]
  if (!meta) return null
  return (
    <span style={{
      display: 'inline-block', padding: '0.1rem 0.5rem', borderRadius: '999px',
      fontSize: '0.65rem', fontWeight: 700, color: meta.color, background: meta.bg,
      border: `1px solid color-mix(in srgb, ${meta.color} 40%, transparent)`,
    }}>
      {meta.label}
    </span>
  )
}

const VIBES = [
  { id: 'citrus',    accord: 'citrus',    emoji: '🍋', title: 'Citrus',         sub: 'Zesty, bright, energising' },
  { id: 'woody',     accord: 'woody',     emoji: '🌲', title: 'Woody',          sub: 'Warm cedar, sandalwood' },
  { id: 'floral',    accord: 'floral',    emoji: '🌸', title: 'Floral',         sub: 'Rose, jasmine, soft' },
  { id: 'amber',     accord: 'amber',     emoji: '🍯', title: 'Amber & Oriental', sub: 'Warm, rich, seductive' },
  { id: 'oud',       accord: 'oud',       emoji: '🕌', title: 'Oud',            sub: 'Bold, dark, Middle Eastern' },
  { id: 'aquatic',   accord: 'aquatic',   emoji: '🌊', title: 'Aquatic & Fresh', sub: 'Ocean, clean, airy' },
  { id: 'vanilla',   accord: 'vanilla',   emoji: '🍦', title: 'Vanilla & Sweet', sub: 'Gourmand, cosy, skin scents' },
  { id: 'aromatic',  accord: 'aromatic',  emoji: '🌿', title: 'Aromatic',       sub: 'Herbs, lavender, green' },
  { id: 'musk',      accord: 'musk',      emoji: '✨', title: 'Musk & Clean',   sub: 'Second-skin, understated' },
  { id: 'powdery',   accord: 'powdery',   emoji: '🧁', title: 'Powdery',        sub: 'Soft, retro, sophisticated' },
]

const SEASONS = [
  { id: 'spring', emoji: '🌸', label: 'Spring', color: '#a78bfa' },
  { id: 'summer', emoji: '☀️', label: 'Summer', color: '#fbbf24' },
  { id: 'fall',   emoji: '🍂', label: 'Fall',   color: '#f97316' },
  { id: 'winter', emoji: '❄️', label: 'Winter', color: '#60a5fa' },
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
      <div style={{ fontSize: '0.85rem', color: '#a78bfa', marginBottom: '0.5rem' }}>
        {p.brand}{displayConcentration(p.concentration) ? ` · ${p.concentration}` : ''}
      </div>
      <div style={{ marginBottom: '0.5rem' }}>
        {(p.accords || []).slice(0, 3).map(a => (
          <span key={a} style={BADGE_STYLE}>{a}</span>
        ))}
      </div>
      {p.community_overall_rating > 0 && (
        <div style={{ fontSize: '0.72rem', color: '#6b7280' }}>
          ★ {p.community_overall_rating?.toFixed(1)}
          {p.rating_count > 0 && <span style={{ marginLeft: '0.35rem' }}>({p.rating_count} ratings)</span>}
        </div>
      )}
    </div>
  )
}

function ResultsGrid({ results, loading, onCardClick, emptyMsg }) {
  if (loading) return <p style={{ textAlign: 'center', color: '#6b7280', padding: '3rem 0' }}>Loading…</p>
  if (!results.length && emptyMsg) return (
    <p style={{ textAlign: 'center', color: '#4b5563', padding: '3rem 0', fontSize: '0.9rem' }}>{emptyMsg}</p>
  )
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: '0.75rem' }}>
      {results.map(p => <PerfumeCard key={p.id} p={p} onClick={onCardClick} />)}
    </div>
  )
}

const TAB_LABELS = ['Search', 'By Gender', 'By Brand', 'By Vibe', 'By Season']

export default function Search() {
  const [tab, setTab] = useState(0)
  const navigate = useNavigate()

  // Search tab
  const [query, setQuery]               = useState('')
  const [brandQ, setBrandQ]             = useState('')
  const [searchResults, setSearchResults] = useState([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [searched, setSearched]         = useState(false)

  // Gender tab
  const [activeGender, setActiveGender] = useState(null)
  const [genderResults, setGenderResults] = useState([])
  const [genderLoading, setGenderLoading] = useState(false)

  // Brand tab
  const [brandList, setBrandList]       = useState([])
  const [brandsLoading, setBrandsLoading] = useState(false)
  const [activeBrand, setActiveBrand]   = useState(null)
  const [brandResults, setBrandResults] = useState([])
  const [brandLoading, setBrandLoading] = useState(false)
  const [brandSearch, setBrandSearch]   = useState('')

  // Vibe tab
  const [activeVibe, setActiveVibe]     = useState(null)
  const [vibeResults, setVibeResults]   = useState([])
  const [vibeLoading, setVibeLoading]   = useState(false)

  // Season tab
  const [activeSeason, setActiveSeason] = useState(null)
  const [seasonResults, setSeasonResults] = useState([])
  const [seasonLoading, setSeasonLoading] = useState(false)

  // Load brand list when brand tab opens
  useEffect(() => {
    if (tab === 2 && brandList.length === 0 && !brandsLoading) {
      setBrandsLoading(true)
      listBrands().then(data => setBrandList(data || [])).finally(() => setBrandsLoading(false))
    }
  }, [tab]) // eslint-disable-line react-hooks/exhaustive-deps

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

  const handleGenderClick = async g => {
    if (activeGender === g) return
    setActiveGender(g)
    setGenderLoading(true)
    setGenderResults([])
    try {
      const data = await browsePerfumes({ gender: g, limit: 50 })
      setGenderResults(data || [])
    } finally {
      setGenderLoading(false)
    }
  }

  const handleBrandClick = async brand => {
    setActiveBrand(brand)
    setBrandLoading(true)
    setBrandResults([])
    try {
      const data = await browsePerfumes({ brand, limit: 100 })
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
      const data = await browsePerfumes({ accord: vibe.accord, limit: 50 })
      setVibeResults(data || [])
    } finally {
      setVibeLoading(false)
    }
  }

  const handleSeasonClick = async season => {
    if (activeSeason === season.id) return
    setActiveSeason(season.id)
    setSeasonLoading(true)
    setSeasonResults([])
    try {
      const data = await browsePerfumes({ season: season.id, limit: 50 })
      setSeasonResults(data || [])
    } finally {
      setSeasonLoading(false)
    }
  }

  const filteredBrands = brandSearch.trim()
    ? brandList.filter(b => b.brand.toLowerCase().includes(brandSearch.toLowerCase()))
    : brandList

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0f', padding: '1.5rem 1.5rem 5rem' }}>
      <h1 style={{ fontSize: '1.75rem', fontWeight: 900, color: '#fff', marginBottom: '1.5rem' }}>
        Browse Perfumes
      </h1>

      {/* Tab bar */}
      <div style={{ borderBottom: '1px solid #1f2937', marginBottom: '2rem', display: 'flex', overflowX: 'auto' }}>
        {TAB_LABELS.map((label, i) => (
          <button key={i} onClick={() => setTab(i)} style={{
            background: 'none', border: 'none', cursor: 'pointer', whiteSpace: 'nowrap',
            borderBottom: `2px solid ${tab === i ? GOLD : 'transparent'}`,
            color: tab === i ? GOLD : '#6b7280',
            fontWeight: tab === i ? 700 : 400,
            fontSize: '0.9rem', padding: '0.65rem 1.25rem',
            marginBottom: '-1px', transition: 'color 0.2s',
          }}>
            {label}
          </button>
        ))}
      </div>

      {/* ── Tab 0: Search ── */}
      {tab === 0 && (
        <div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem', marginBottom: '1.5rem' }}>
            <input
              style={{ flex: '1 1 200px', background: CARD_BG, border: '1px solid #374151', borderRadius: '8px', color: '#fff', fontSize: '0.95rem', padding: '0.7rem 1rem', outline: 'none' }}
              placeholder="Search by name…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <input
              style={{ flex: '0 1 180px', background: CARD_BG, border: '1px solid #374151', borderRadius: '8px', color: '#fff', fontSize: '0.95rem', padding: '0.7rem 1rem', outline: 'none' }}
              placeholder="Filter by brand…"
              value={brandQ}
              onChange={e => setBrandQ(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={searchLoading}
              style={{ background: '#7c3aed', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 600, fontSize: '0.95rem', padding: '0.7rem 1.5rem', opacity: searchLoading ? 0.7 : 1 }}
            >
              {searchLoading ? 'Searching…' : 'Search'}
            </button>
          </div>
          <ResultsGrid results={searchResults} loading={searchLoading} onCardClick={goToPerfume}
            emptyMsg={searched ? 'No results found.' : 'Search for a perfume above to browse the database.'} />
        </div>
      )}

      {/* ── Tab 1: By Gender ── */}
      {tab === 1 && (
        <div>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '2rem' }}>
            {[
              { key: 'masculine', emoji: '🔵', label: 'For Him', sub: 'Masculine + unisex', color: '#60a5fa' },
              { key: 'feminine',  emoji: '🌸', label: 'For Her', sub: 'Feminine + unisex',  color: '#f9a8d4' },
              { key: 'unisex',    emoji: '⚪', label: 'Unisex',  sub: 'All genders welcome', color: '#a78bfa' },
            ].map(g => {
              const isActive = activeGender === g.key
              return (
                <div key={g.key} onClick={() => handleGenderClick(g.key)} style={{
                  flex: '1 1 160px', background: isActive ? `rgba(201,168,76,0.08)` : CARD_BG,
                  border: `2px solid ${isActive ? GOLD : BORDER_GOLD}`,
                  borderRadius: '14px', padding: '1.5rem 1rem', cursor: 'pointer', textAlign: 'center',
                  transition: 'all 0.18s',
                }}>
                  <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>{g.emoji}</div>
                  <div style={{ fontWeight: 700, color: isActive ? GOLD : g.color, fontSize: '1rem' }}>{g.label}</div>
                  <div style={{ fontSize: '0.73rem', color: '#6b7280', marginTop: '0.2rem' }}>{g.sub}</div>
                </div>
              )
            })}
          </div>
          {activeGender && (
            <>
              <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '1rem' }}>
                Top {genderResults.length} by rating count
              </div>
              <ResultsGrid results={genderResults} loading={genderLoading} onCardClick={goToPerfume}
                emptyMsg="No results." />
            </>
          )}
          {!activeGender && (
            <p style={{ textAlign: 'center', color: '#4b5563', padding: '3rem 0', fontSize: '0.9rem' }}>
              Choose a gender to see the top-rated perfumes.
            </p>
          )}
        </div>
      )}

      {/* ── Tab 2: By Brand ── */}
      {tab === 2 && (
        <div>
          {/* Brand search filter */}
          <input
            style={{ width: '100%', maxWidth: '320px', background: CARD_BG, border: '1px solid #374151', borderRadius: '8px', color: '#fff', fontSize: '0.9rem', padding: '0.6rem 1rem', outline: 'none', marginBottom: '1rem', boxSizing: 'border-box' }}
            placeholder="Filter brands…"
            value={brandSearch}
            onChange={e => setBrandSearch(e.target.value)}
          />
          {brandsLoading && <p style={{ color: '#6b7280' }}>Loading brands…</p>}
          {!brandsLoading && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.5rem', marginBottom: '2rem', maxHeight: activeBrand ? '200px' : '420px', overflowY: 'auto' }}>
              {filteredBrands.map(b => {
                const isActive = activeBrand === b.brand
                return (
                  <div key={b.brand} onClick={() => handleBrandClick(b.brand)} style={{
                    background: isActive ? 'rgba(201,168,76,0.1)' : CARD_BG,
                    border: `1px solid ${isActive ? GOLD : BORDER_GOLD}`,
                    borderRadius: '8px', padding: '0.5rem 0.75rem',
                    cursor: 'pointer', textAlign: 'center',
                    fontSize: '0.75rem', fontWeight: isActive ? 700 : 400,
                    color: isActive ? GOLD : '#d1d5db',
                    transition: 'all 0.15s', lineHeight: 1.3,
                  }}>
                    {b.brand}
                    <div style={{ fontSize: '0.65rem', color: '#4b5563' }}>{b.count}</div>
                  </div>
                )
              })}
            </div>
          )}
          {activeBrand ? (
            <>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '1rem' }}>
                <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: GOLD, margin: 0 }}>{activeBrand}</h2>
                {!brandLoading && <span style={{ fontSize: '0.8rem', color: '#6b7280' }}>{brandResults.length} perfumes</span>}
              </div>
              <ResultsGrid results={brandResults} loading={brandLoading} onCardClick={goToPerfume}
                emptyMsg="No results for this brand." />
            </>
          ) : !brandsLoading && (
            <p style={{ textAlign: 'center', color: '#4b5563', padding: '2rem 0', fontSize: '0.9rem' }}>
              Select a brand to see its perfumes.
            </p>
          )}
        </div>
      )}

      {/* ── Tab 3: By Vibe ── */}
      {tab === 3 && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: '0.75rem', marginBottom: '2rem' }}>
            {VIBES.map(vibe => {
              const isActive = activeVibe === vibe.id
              return (
                <div key={vibe.id} onClick={() => handleVibeClick(vibe)} style={{
                  background: isActive ? 'rgba(201,168,76,0.08)' : 'linear-gradient(135deg, #111827 0%, #0d1117 100%)',
                  border: `1px solid ${isActive ? GOLD : BORDER_GOLD}`,
                  borderRadius: '12px', padding: '1rem', cursor: 'pointer', textAlign: 'left',
                  transition: 'all 0.18s', boxShadow: isActive ? `0 0 18px rgba(201,168,76,0.18)` : 'none',
                }}>
                  <div style={{ fontSize: '1.5rem', marginBottom: '0.35rem' }}>{vibe.emoji}</div>
                  <div style={{ fontWeight: 700, fontSize: '0.85rem', color: isActive ? GOLD : '#e5e7eb', marginBottom: '0.2rem' }}>{vibe.title}</div>
                  <div style={{ fontSize: '0.7rem', color: '#6b7280', lineHeight: 1.4 }}>{vibe.sub}</div>
                </div>
              )
            })}
          </div>
          {activeVibe ? (
            <>
              <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '1rem' }}>
                Top {vibeResults.length} by community rating
              </div>
              <ResultsGrid results={vibeResults} loading={vibeLoading} onCardClick={goToPerfume}
                emptyMsg="No perfumes matched this vibe." />
            </>
          ) : (
            <p style={{ textAlign: 'center', color: '#4b5563', padding: '2rem 0', fontSize: '0.9rem' }}>
              Select a vibe to find matching perfumes.
            </p>
          )}
        </div>
      )}

      {/* ── Tab 4: By Season ── */}
      {tab === 4 && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', maxWidth: '500px', marginBottom: '2.5rem' }}>
            {SEASONS.map(s => {
              const isActive = activeSeason === s.id
              return (
                <div key={s.id} onClick={() => handleSeasonClick(s)} style={{
                  background: isActive ? 'rgba(201,168,76,0.08)' : CARD_BG,
                  border: `2px solid ${isActive ? GOLD : BORDER_GOLD}`,
                  borderRadius: '14px', padding: '1.5rem', cursor: 'pointer', textAlign: 'center',
                  transition: 'all 0.18s',
                }}>
                  <div style={{ fontSize: '2.5rem', marginBottom: '0.4rem' }}>{s.emoji}</div>
                  <div style={{ fontWeight: 700, fontSize: '1rem', color: isActive ? GOLD : s.color }}>{s.label}</div>
                </div>
              )
            })}
          </div>
          {activeSeason ? (
            <>
              <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '1rem' }}>
                Top {seasonResults.length} perfumes by {activeSeason} votes
              </div>
              <ResultsGrid results={seasonResults} loading={seasonLoading} onCardClick={goToPerfume}
                emptyMsg="No perfumes found for this season." />
            </>
          ) : (
            <p style={{ textAlign: 'center', color: '#4b5563', padding: '2rem 0', fontSize: '0.9rem' }}>
              Pick a season to see the most-voted perfumes.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
