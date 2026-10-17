/**
 * Compare page — side-by-side fragrance comparison.
 *
 * URL: /compare?a=Sauvage&ab=Dior&b=Bleu+de+Chanel&bb=Chanel
 * Query params: a (name A), ab (brand A), b (name B), bb (brand B)
 *
 * Phase 7 UI polish.
 */
import React, { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { predictPerfume, searchPerfumes } from '../api/client.js'
import { displayConcentration } from '../utils/concentration.js'

// ── helpers ───────────────────────────────────────────────────────────────────

function cap(s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : '' }
function fmt1(v) { return v != null && !isNaN(v) ? parseFloat(v).toFixed(1) : '–' }

const GOLD = '#C9A84C'
const GOLD_FAINT = 'rgba(201,168,76,0.10)'
const GOLD_BORDER = 'rgba(201,168,76,0.20)'
const CARD_BG = 'linear-gradient(135deg, #141A2E 0%, #111729 100%)'
const SURFACE = '#111729'

// Scores to compare: [key, label, max]
const COMPARE_ROWS = [
  { key: 'longevity_hours',     label: 'Longevity (hours)', max: 12, fmt: v => `${fmt1(v)}h` },
  { key: 'sillage_score',       label: 'Sillage',           max: 10, fmt: v => fmt1(v) },
  { key: 'blind_buy_score',     label: 'Blind Buy',         max: 10, fmt: v => fmt1(v) },
  { key: 'versatility_score',   label: 'Versatility',       max: 10, fmt: v => fmt1(v) },
  { key: 'compliment_score',    label: 'Compliments',       max: 10, fmt: v => fmt1(v) },
  { key: 'cost_per_wear_score', label: 'Value / Wear',      max: 10, fmt: v => fmt1(v) },
  { key: 'temp_optimal_min_c',  label: 'Optimal temp',      max: null, fmt: (v, p) => `${fmt1(v)}°–${fmt1(p.temp_optimal_max_c)}°C` },
  { key: 'performance_peak_hour', label: 'Peaks at',        max: 12, fmt: v => `${fmt1(v)}h` },
]

const SEASON_KEYS = [
  { key: 'season_spring', label: 'Spring' },
  { key: 'season_summer', label: 'Summer' },
  { key: 'season_fall',   label: 'Fall'   },
  { key: 'season_winter', label: 'Winter' },
]

const OCC_KEYS = [
  { key: 'occ_office', label: 'Office' },
  { key: 'occ_date',   label: 'Date'   },
  { key: 'occ_casual', label: 'Casual' },
  { key: 'occ_sport',  label: 'Sport'  },
]

const ACCENT_A = GOLD
const ACCENT_B = '#6B9BC4'   // blue for the second fragrance

function scoreColor(v, accent) {
  if (v == null || isNaN(v)) return '#4A4235'
  return accent
}

// ── mini components ───────────────────────────────────────────────────────────

function SearchInput({ label, accent, name, setName, brand, setBrand, onSearch, loading }) {
  const [sugs, setSugs] = useState([])
  const [showSugs, setShowSugs] = useState(false)
  const abortRef = useRef(null)
  const containerRef = useRef(null)

  useEffect(() => {
    const handleOutsideClick = e => {
      if (containerRef.current && !containerRef.current.contains(e.target)) setShowSugs(false)
    }
    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  useEffect(() => {
    if (name.length < 2) { setSugs([]); return }
    const timer = setTimeout(async () => {
      abortRef.current?.abort()
      const ctrl = new AbortController(); abortRef.current = ctrl
      try {
        const res = await searchPerfumes(name, undefined, ctrl.signal)
        setSugs(res.slice(0, 5))
        setShowSugs(true)
      } catch {}
    }, 150)
    return () => clearTimeout(timer)
  }, [name])

  const pick = sg => {
    setName(sg.name)
    setBrand(sg.brand)
    setSugs([])
    setShowSugs(false)
    onSearch(sg.name, sg.brand, sg.id)
  }

  return (
    <div ref={containerRef} style={{ flex: 1, minWidth: 0 }}>
      <p className="text-xs font-bold uppercase tracking-widest mb-2" style={{ color: accent }}>
        {label}
      </p>
      <div className="relative">
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && onSearch(name, brand, null)}
          placeholder="Fragrance name…"
          className="w-full px-4 py-2.5 rounded-xl text-sm"
          style={{
            background: SURFACE, border: `1px solid ${accent}40`,
            color: '#E8DCC8', outline: 'none',
          }}
        />
        {showSugs && sugs.length > 0 && (
          <div style={{
            position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 20,
            background: '#141A2E', border: '1px solid ' + GOLD_BORDER, borderRadius: '8px',
            marginTop: '4px', maxHeight: '220px', overflowY: 'auto',
          }}>
            {sugs.map(sg => (
              <div
                key={sg.id}
                onClick={() => pick(sg)}
                className="px-4 py-2.5 cursor-pointer text-sm"
                style={{ borderBottom: '1px solid rgba(201,168,76,0.08)', color: '#E8DCC8' }}
                onMouseEnter={e => e.currentTarget.style.background = GOLD_FAINT}
                onMouseLeave={e => e.currentTarget.style.background = ''}
              >
                <strong>{sg.name}</strong>
                <span style={{ color: GOLD, marginLeft: '0.5rem', fontSize: '0.75rem' }}>{sg.brand}</span>
                {displayConcentration(sg.concentration) && (
                  <span style={{
                    display: 'inline-block', marginLeft: '0.4rem',
                    padding: '0.05rem 0.35rem', borderRadius: '999px',
                    fontSize: '0.62rem', fontWeight: 700, color: GOLD,
                    background: GOLD_FAINT, border: `1px solid ${GOLD_BORDER}`,
                  }}>
                    {sg.concentration}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
      <input
        value={brand}
        onChange={e => setBrand(e.target.value)}
        placeholder="Brand (optional)"
        className="w-full mt-2 px-4 py-2 rounded-xl text-sm"
        style={{ background: SURFACE, border: `1px solid ${GOLD_BORDER}`, color: '#E8DCC8', outline: 'none' }}
      />
    </div>
  )
}

function CompareRow({ rowDef, a, b }) {
  const va = a ? (rowDef.fmt ? rowDef.fmt(a[rowDef.key], a) : fmt1(a[rowDef.key])) : '–'
  const vb = b ? (rowDef.fmt ? rowDef.fmt(b[rowDef.key], b) : fmt1(b[rowDef.key])) : '–'
  const numA = a ? parseFloat(a[rowDef.key]) : null
  const numB = b ? parseFloat(b[rowDef.key]) : null
  const maxV = rowDef.max || 10
  const pctA = numA != null && !isNaN(numA) ? Math.min(100, (numA / maxV) * 100) : 0
  const pctB = numB != null && !isNaN(numB) ? Math.min(100, (numB / maxV) * 100) : 0

  const aWins = numA != null && numB != null && numA > numB
  const bWins = numA != null && numB != null && numB > numA

  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-xs font-semibold" style={{ color: aWins ? ACCENT_A : '#5A5245' }}>{va}</span>
        <span className="text-[0.65rem] uppercase tracking-widest" style={{ color: '#3A3428' }}>{rowDef.label}</span>
        <span className="text-xs font-semibold" style={{ color: bWins ? ACCENT_B : '#5A5245' }}>{vb}</span>
      </div>
      <div className="relative h-2 rounded-full" style={{ background: '#1A2035' }}>
        {/* A bar — grows from left */}
        <div
          className="absolute left-0 top-0 h-full rounded-l-full transition-all duration-700"
          style={{ width: `${pctA / 2}%`, background: ACCENT_A, opacity: 0.85 }}
        />
        {/* B bar — grows from right */}
        <div
          className="absolute right-0 top-0 h-full rounded-r-full transition-all duration-700"
          style={{ width: `${pctB / 2}%`, background: ACCENT_B, opacity: 0.85 }}
        />
        {/* centre divider */}
        <div className="absolute left-1/2 top-0 h-full w-px" style={{ background: '#2A3045' }} />
      </div>
    </div>
  )
}

function AccordChips({ accords, accent }) {
  if (!accords?.length) return <span style={{ color: '#3A3428', fontSize: '0.72rem' }}>–</span>
  return (
    <div className="flex flex-wrap gap-1">
      {accords.slice(0, 5).map(a => (
        <span
          key={a}
          className="px-2 py-0.5 rounded-full text-xs"
          style={{ background: `${accent}10`, border: `1px solid ${accent}35`, color: '#E8DCC8' }}
        >
          {a}
        </span>
      ))}
    </div>
  )
}

function NotePyramid({ top, mid, base, accent }) {
  const render = (notes, label) => (
    <div className="mb-2">
      <p className="text-[0.6rem] uppercase font-bold mb-1" style={{ color: accent }}>{label}</p>
      <div className="flex flex-wrap gap-1">
        {(notes || []).slice(0, 4).map(n => (
          <span key={n} className="text-xs px-1.5 py-0.5 rounded" style={{ background: '#1A2035', color: '#9B8E7A' }}>{n}</span>
        ))}
        {!notes?.length && <span style={{ color: '#3A3428', fontSize: '0.72rem' }}>–</span>}
      </div>
    </div>
  )
  return (
    <div>
      {render(top, 'Top')}
      {render(mid, 'Heart')}
      {render(base, 'Base')}
    </div>
  )
}

function SeasonRow({ keys, a, b }) {
  return (
    <div className="grid grid-cols-4 gap-1">
      {keys.map(({ key, label }) => {
        const va = a?.[key] ?? 0
        const vb = b?.[key] ?? 0
        return (
          <div key={key} className="text-center">
            <p className="text-[0.6rem] mb-0.5" style={{ color: '#3A3428' }}>{label}</p>
            <p className="text-xs font-bold" style={{ color: va >= vb ? ACCENT_A : '#5A5245' }}>{fmt1(va)}</p>
            <div className="my-0.5 h-1 rounded-full" style={{ background: '#1A2035' }}>
              <div style={{ background: ACCENT_A, height: '100%', borderRadius: '999px', width: `${(va / 10) * 100}%` }} />
            </div>
            <div className="h-1 rounded-full" style={{ background: '#1A2035' }}>
              <div style={{ background: ACCENT_B, height: '100%', borderRadius: '999px', width: `${(vb / 10) * 100}%` }} />
            </div>
            <p className="text-xs font-bold mt-0.5" style={{ color: vb > va ? ACCENT_B : '#5A5245' }}>{fmt1(vb)}</p>
          </div>
        )
      })}
    </div>
  )
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function Compare() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const [nameA, setNameA] = useState(searchParams.get('a') || '')
  const [brandA, setBrandA] = useState(searchParams.get('ab') || '')
  const [nameB, setNameB] = useState(searchParams.get('b') || '')
  const [brandB, setBrandB] = useState(searchParams.get('bb') || '')

  const [resultA, setResultA] = useState(null)
  const [resultB, setResultB] = useState(null)
  const [loadingA, setLoadingA] = useState(false)
  const [loadingB, setLoadingB] = useState(false)
  const [errorA, setErrorA] = useState(null)
  const [errorB, setErrorB] = useState(null)

  const fetchA = async (name, brand, id = null) => {
    if (!name) return
    setLoadingA(true); setErrorA(null)
    try { setResultA(await predictPerfume(name, brand, null, id)) }
    catch (e) { setErrorA(e.response?.data?.detail || e.message) }
    finally { setLoadingA(false) }
  }

  const fetchB = async (name, brand, id = null) => {
    if (!name) return
    setLoadingB(true); setErrorB(null)
    try { setResultB(await predictPerfume(name, brand, null, id)) }
    catch (e) { setErrorB(e.response?.data?.detail || e.message) }
    finally { setLoadingB(false) }
  }

  // Auto-fetch from URL params on mount
  useEffect(() => {
    const a = searchParams.get('a'), ab = searchParams.get('ab')
    const b = searchParams.get('b'), bb = searchParams.get('bb')
    if (a) fetchA(a, ab || '')
    if (b) fetchB(b, bb || '')
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const pa = resultA?.predictions
  const pb = resultB?.predictions

  return (
    <div className="min-h-screen px-4 pb-16 pt-8 sm:px-6 md:px-8">
      <div className="max-w-5xl mx-auto">

        {/* Page title */}
        <h1
          className="text-2xl sm:text-3xl font-bold text-center mb-2"
          style={{ color: '#E8DCC8', fontFamily: "'Playfair Display', Georgia, serif" }}
        >
          Compare Fragrances
        </h1>
        <p className="text-xs text-center mb-8" style={{ color: '#4A4235' }}>
          Side-by-side performance, season, and character analysis
        </p>

        {/* Search inputs */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <SearchInput
            label="Fragrance A"
            accent={ACCENT_A}
            name={nameA} setName={setNameA}
            brand={brandA} setBrand={setBrandA}
            onSearch={fetchA}
            loading={loadingA}
          />
          <div className="flex items-center justify-center shrink-0" style={{ color: '#3A3428', fontSize: '1.2rem' }}>
            vs
          </div>
          <SearchInput
            label="Fragrance B"
            accent={ACCENT_B}
            name={nameB} setName={setNameB}
            brand={brandB} setBrand={setBrandB}
            onSearch={fetchB}
            loading={loadingB}
          />
        </div>

        {/* Identity header — shown as soon as at least one is loaded */}
        {(resultA || resultB) && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            {/* Card A */}
            <div
              className="p-4 rounded-2xl"
              style={{ background: CARD_BG, border: `1px solid ${ACCENT_A}30` }}
            >
              {resultA ? (
                <>
                  <p className="text-xs font-semibold mb-0.5" style={{ color: ACCENT_A }}>{resultA.perfume.brand}</p>
                  <p className="text-lg font-bold leading-tight" style={{ color: '#E8DCC8', fontFamily: "'Playfair Display', Georgia, serif" }}>
                    {resultA.perfume.name}
                  </p>
                  {displayConcentration(resultA.perfume.concentration) && (
                    <span style={{
                      display: 'inline-block', marginTop: '0.25rem',
                      padding: '0.05rem 0.4rem', borderRadius: '999px',
                      fontSize: '0.62rem', fontWeight: 700, color: ACCENT_A,
                      background: GOLD_FAINT, border: `1px solid ${GOLD_BORDER}`,
                    }}>
                      {resultA.perfume.concentration}
                    </span>
                  )}
                  <div className="mt-2">
                    <AccordChips accords={resultA.perfume.accords} accent={ACCENT_A} />
                  </div>
                </>
              ) : (
                <p className="text-sm" style={{ color: '#3A3428' }}>{loadingA ? 'Loading…' : 'Enter a fragrance above'}</p>
              )}
              {errorA && <p className="text-xs mt-2" style={{ color: '#C4614A' }}>{errorA}</p>}
            </div>

            {/* Card B */}
            <div
              className="p-4 rounded-2xl"
              style={{ background: CARD_BG, border: `1px solid ${ACCENT_B}30` }}
            >
              {resultB ? (
                <>
                  <p className="text-xs font-semibold mb-0.5" style={{ color: ACCENT_B }}>{resultB.perfume.brand}</p>
                  <p className="text-lg font-bold leading-tight" style={{ color: '#E8DCC8', fontFamily: "'Playfair Display', Georgia, serif" }}>
                    {resultB.perfume.name}
                  </p>
                  {displayConcentration(resultB.perfume.concentration) && (
                    <span style={{
                      display: 'inline-block', marginTop: '0.25rem',
                      padding: '0.05rem 0.4rem', borderRadius: '999px',
                      fontSize: '0.62rem', fontWeight: 700, color: ACCENT_A,
                      background: GOLD_FAINT, border: `1px solid ${GOLD_BORDER}`,
                    }}>
                      {resultB.perfume.concentration}
                    </span>
                  )}
                  <div className="mt-2">
                    <AccordChips accords={resultB.perfume.accords} accent={ACCENT_B} />
                  </div>
                </>
              ) : (
                <p className="text-sm" style={{ color: '#3A3428' }}>{loadingB ? 'Loading…' : 'Enter a fragrance above'}</p>
              )}
              {errorB && <p className="text-xs mt-2" style={{ color: '#C4614A' }}>{errorB}</p>}
            </div>
          </div>
        )}

        {/* Legend */}
        {(pa || pb) && (
          <div className="flex justify-center gap-6 mb-4 text-xs">
            <span style={{ color: ACCENT_A }}>■ {resultA?.perfume.name || 'A'}</span>
            <span style={{ color: ACCENT_B }}>■ {resultB?.perfume.name || 'B'}</span>
          </div>
        )}

        {/* Score comparison rows */}
        {(pa || pb) && (
          <div
            className="rounded-2xl p-4 sm:p-6 mb-6"
            style={{ background: SURFACE, border: `1px solid ${GOLD_BORDER}` }}
          >
            <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: '#4A4235' }}>
              Performance Scores
            </p>
            {COMPARE_ROWS.map(row => (
              <CompareRow key={row.key} rowDef={row} a={pa} b={pb} />
            ))}
          </div>
        )}

        {/* Season comparison */}
        {(pa || pb) && (
          <div
            className="rounded-2xl p-4 sm:p-6 mb-6"
            style={{ background: SURFACE, border: `1px solid ${GOLD_BORDER}` }}
          >
            <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: '#4A4235' }}>
              Season Fit
            </p>
            <SeasonRow keys={SEASON_KEYS} a={pa} b={pb} />
            <div className="mt-5">
              <p className="text-xs font-bold uppercase tracking-widest mb-4" style={{ color: '#4A4235' }}>
                Occasion Fit
              </p>
              <SeasonRow keys={OCC_KEYS} a={pa} b={pb} />
            </div>
          </div>
        )}

        {/* Note pyramids */}
        {(resultA || resultB) && (
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="rounded-2xl p-4" style={{ background: SURFACE, border: `1px solid ${ACCENT_A}20` }}>
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: ACCENT_A }}>
                {resultA?.perfume.name || 'A'} · Notes
              </p>
              <NotePyramid
                top={resultA?.perfume.top_notes}
                mid={resultA?.perfume.middle_notes}
                base={resultA?.perfume.base_notes}
                accent={ACCENT_A}
              />
            </div>
            <div className="rounded-2xl p-4" style={{ background: SURFACE, border: `1px solid ${ACCENT_B}20` }}>
              <p className="text-xs font-bold uppercase tracking-widest mb-3" style={{ color: ACCENT_B }}>
                {resultB?.perfume.name || 'B'} · Notes
              </p>
              <NotePyramid
                top={resultB?.perfume.top_notes}
                mid={resultB?.perfume.middle_notes}
                base={resultB?.perfume.base_notes}
                accent={ACCENT_B}
              />
            </div>
          </div>
        )}

        {/* Prompt if nothing loaded yet */}
        {!resultA && !resultB && !loadingA && !loadingB && (
          <div className="text-center py-16">
            <p style={{ color: '#3A3428', fontSize: '0.85rem' }}>
              Search two fragrances above to compare them side by side.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
