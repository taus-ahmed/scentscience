import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import PerfumeSearch from '../components/PerfumeSearch.jsx'
import ScoreCard from '../components/ScoreCard.jsx'
import SeasonBars, { OccasionRanking } from '../components/RadarChart.jsx'
import LongevityDecayChart, { TimeOfDayChart } from '../components/BarChart.jsx'
import PieChart from '../components/PieChart.jsx'
import NLPConclusion from '../components/NLPConclusion.jsx'
import FamilyRadar from '../components/FamilyRadar.jsx'
import ContextHeatmap from '../components/ContextHeatmap.jsx'
import OutOfDBPanel from '../components/OutOfDBPanel.jsx'
import { predictPerfume, predictFromNotes } from '../api/client.js'
import { getCityRecommendations } from '../utils/cityRecommendations.js'

const PAGE_BG = { background: 'transparent', position: 'relative', zIndex: 1 }

const PERFUME_CARD_STYLE = {
  background: 'linear-gradient(135deg, #141A2E 0%, #111729 100%)',
  borderRadius: '16px', border: '1px solid rgba(201,168,76,0.2)',
}
const ACCORD_BADGE = {
  display: 'inline-block', padding: '0.2rem 0.6rem',
  background: 'rgba(201,168,76,0.08)', borderRadius: '999px',
  fontSize: '0.72rem', color: '#C9A84C',
  border: '1px solid rgba(201,168,76,0.25)',
  marginRight: '0.4rem', marginBottom: '0.3rem',
}

const FAMILY_COLORS = {
  citrus: '#D4B86A', woody: '#8B6914', floral: '#C4859A',
  oriental: '#C9A84C', fresh: '#5DB89C', gourmand: '#D4956B',
  chypre: '#7B9E6B', fougere: '#5B9BB5', aquatic: '#6B9BC4',
  spicy: '#C4614A', earthy: '#6B8B4A', green: '#7DAF6B',
  powdery: '#C4A8B5', smoky: '#7A7065', resinous: '#A87D3C',
  musky: '#C9B5A0', animalic: '#6B4A1C',
}

const OCC_LABELS = {
  occ_office: 'office', occ_date: 'date nights', occ_casual: 'casual',
  occ_formal: 'formal', occ_sport: 'sport', occ_travel: 'travel',
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
      className="px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap"
      style={{
        background: meta.bg,
        border: `1px solid color-mix(in srgb, ${meta.color} 40%, transparent)`,
        color: meta.color,
      }}
    >
      {meta.label}
    </span>
  )
}

function scoreColor(v) {
  if (v == null || isNaN(v)) return '#C9A84C'
  if (v > 7) return '#5DB89C'
  if (v >= 4) return '#C9A84C'
  return '#C4614A'
}

function pickMax(entries) {
  return entries.reduce((m, c) => (c[1] || 0) > (m[1] || 0) ? c : m)[0]
}

function bestWornSentence(p) {
  const season = pickMax([
    ['spring', p.season_spring], ['summer', p.season_summer],
    ['fall',   p.season_fall],   ['winter', p.season_winter],
  ])
  const time = pickMax([
    ['morning', p.time_morning], ['afternoon', p.time_afternoon],
    ['evening', p.time_evening], ['night',     p.time_night],
  ])
  const occ = pickMax(Object.entries(OCC_LABELS).map(([k, v]) => [v, p[k]]))
  const cap = s => s.charAt(0).toUpperCase() + s.slice(1)
  return `Best for ${cap(time)} · ${cap(season)} · ${cap(occ)}`
}

// ─── inline sub-components ───────────────────────────────────────────────────

function HeadlineScore({ label, value, sub, color }) {
  return (
    <div
      className="flex flex-col items-center text-center p-3 sm:p-6 rounded-2xl glass-card min-w-0"
      style={{ background: '#111729', border: `1px solid ${color}25` }}
    >
      <span className="text-[0.65rem] sm:text-xs font-semibold uppercase tracking-wide sm:tracking-widest mb-2 leading-tight" style={{ color: '#4A4235' }}>
        {label}
      </span>
      <span
        className="text-2xl sm:text-5xl font-black leading-none mb-1.5"
        style={{ color, fontFamily: "'Playfair Display', Georgia, serif", whiteSpace: 'nowrap' }}
      >
        {value}
      </span>
      <span className="text-[0.65rem] sm:text-xs leading-tight" style={{ color: '#4A4235' }}>{sub}</span>
    </div>
  )
}

function SectionDivider({ label }) {
  return (
    <div className="flex items-center gap-3 my-6">
      <div className="flex-1 h-px" style={{ background: 'rgba(201,168,76,0.12)' }} />
      {label && (
        <span
          className="text-xs font-bold uppercase tracking-widest"
          style={{ color: '#4A4235', fontFamily: "'Playfair Display', Georgia, serif", letterSpacing: '0.12em' }}
        >
          {label}
        </span>
      )}
      <div className="flex-1 h-px" style={{ background: 'rgba(201,168,76,0.12)' }} />
    </div>
  )
}

function FamilyChips({ familyFeatures }) {
  if (!familyFeatures || typeof familyFeatures !== 'object') return null
  const top = Object.entries(familyFeatures)
    .filter(([, v]) => v > 0.05)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
  if (!top.length) return null
  return (
    <div className="flex flex-wrap gap-1.5 mt-2">
      {top.map(([fam]) => {
        const c = FAMILY_COLORS[fam] || '#8B7355'
        return (
          <span
            key={fam}
            style={{
              padding: '0.15rem 0.55rem', borderRadius: '999px',
              fontSize: '0.7rem', background: `${c}18`,
              border: `1px solid ${c}50`, color: c,
            }}
          >
            {fam[0].toUpperCase() + fam.slice(1)}
          </span>
        )
      })}
    </div>
  )
}

function PersonFitBadges({ predictions: p }) {
  const categories = [
    {
      label: 'Skin',
      best: pickMax([['Dry', p.skin_dry_score], ['Oily', p.skin_oily_score], ['Combo', p.skin_combo_score]]),
    },
    {
      label: 'Age',
      best: pickMax([['18–25', p.age_18_25], ['25–35', p.age_25_35], ['35–50', p.age_35_50], ['50+', p.age_50_plus]]),
    },
    {
      label: 'Vibe',
      best: pickMax([
        ['Dominant', p.personality_dominant], ['Intellectual', p.personality_intellectual],
        ['Casual', p.personality_casual], ['Romantic', p.personality_romantic],
      ]),
    },
    {
      label: 'Gender',
      best: pickMax([['Masculine', p.gender_masculine], ['Feminine', p.gender_feminine], ['Unisex', p.gender_unisex]]),
    },
  ]

  return (
    <div className="flex flex-wrap gap-2 mb-2 py-3">
      {categories.map(({ label, best }) => (
        <div
          key={label}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs"
          style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.12)' }}
        >
          <span style={{ color: '#4A4235' }}>{label}:</span>
          <span className="font-semibold" style={{ color: '#9B8E7A' }}>{best}</span>
        </div>
      ))}
    </div>
  )
}

const PARTICLE_DATA = Array.from({ length: 24 }, (_, i) => ({
  left:     `${((i * 37 + i * i * 7) % 97)}%`,
  size:     i % 3 === 0 ? '2px' : '1px',
  delay:    `-${(i * 1.3) % 12}s`,
  duration: `${10 + (i % 7) * 1.5}s`,
  opacity:  0.18 + (i % 5) * 0.06,
  drift:    `${(i % 2 === 0 ? 1 : -1) * (8 + (i % 12) * 2)}px`,
}))

function Particles() {
  return (
    <div style={{ position: 'fixed', inset: 0, pointerEvents: 'none', overflow: 'hidden', zIndex: 0 }}>
      {PARTICLE_DATA.map((pt, i) => (
        <span
          key={i}
          style={{
            position: 'absolute',
            bottom: '-2px',
            left: pt.left,
            width: pt.size,
            height: pt.size,
            borderRadius: '50%',
            background: `rgba(201,168,76,${pt.opacity})`,
            animation: `particle-float ${pt.duration} ${pt.delay} infinite linear`,
            '--p-drift': pt.drift,
          }}
        />
      ))}
    </div>
  )
}

function CollapsibleSection({ label, children }) {
  return (
    <details className="mb-3">
      <summary
        className="flex items-center justify-between cursor-pointer select-none px-4 py-3 rounded-xl text-xs font-bold uppercase tracking-widest"
        style={{ background: '#0D1117', color: '#4A4235', border: '1px solid rgba(201,168,76,0.10)', listStyle: 'none' }}
      >
        <span>{label}</span>
        <span style={{ fontSize: '0.65rem', opacity: 0.5 }}>expand</span>
      </summary>
      <div className="pt-3">{children}</div>
    </details>
  )
}

function FullPersonFit({ predictions: p }) {
  const skinData = [
    { label: 'Dry Skin',   value: p.skin_dry_score,  color: '#C9A84C' },
    { label: 'Oily Skin',  value: p.skin_oily_score,  color: '#D4956B' },
    { label: 'Combo Skin', value: p.skin_combo_score, color: '#8B7355' },
  ]
  const ageData = [
    { label: '18–25', value: p.age_18_25 },
    { label: '25–35', value: p.age_25_35 },
    { label: '35–50', value: p.age_35_50 },
    { label: '50+',   value: p.age_50_plus },
  ]
  const personData = [
    { label: 'Dominant',     value: p.personality_dominant,     color: '#C4614A' },
    { label: 'Intellectual', value: p.personality_intellectual, color: '#6B9BC4' },
    { label: 'Casual',       value: p.personality_casual,       color: '#5DB89C' },
    { label: 'Romantic',     value: p.personality_romantic,     color: '#C47D9A' },
  ]
  const genderData = [
    { label: 'Masculine', value: p.gender_masculine, color: '#6B9BC4' },
    { label: 'Feminine',  value: p.gender_feminine,  color: '#C47D9A' },
    { label: 'Unisex',    value: p.gender_unisex,    color: '#5DB89C' },
  ]

  const Bar = ({ label, value, color = '#C9A84C' }) => (
    <div className="mb-2.5">
      <div className="flex justify-between mb-1">
        <span className="text-xs" style={{ color: '#E8DCC8' }}>{label}</span>
        <span className="text-xs font-bold" style={{ color }}>{value?.toFixed(1)}</span>
      </div>
      <div className="h-1 rounded-full" style={{ background: '#1A2035' }}>
        <div className="h-full rounded-full" style={{ background: color, width: `${((value ?? 0) / 10) * 100}%` }} />
      </div>
    </div>
  )

  return (
    <div className="rounded-xl p-4 sm:p-6 mb-4 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#7A6E5F' }}>Skin Type</p>
          {skinData.map(d => <Bar key={d.label} {...d} />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#7A6E5F' }}>Age Bracket</p>
          {ageData.map(d => <Bar key={d.label} {...d} color="#C9A84C" />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#7A6E5F' }}>Personality</p>
          {personData.map(d => <Bar key={d.label} {...d} />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#7A6E5F' }}>Gender Expression</p>
          {genderData.map(d => <Bar key={d.label} {...d} />)}
        </div>
      </div>
    </div>
  )
}

function ClimateChart({ predictions: p }) {
  const data = [
    { name: 'Tropical',   value: parseFloat((p.climate_tropical  ?? 0).toFixed(1)), color: '#C9A84C' },
    { name: 'Arid',       value: parseFloat((p.climate_arid       ?? 0).toFixed(1)), color: '#D4956B' },
    { name: 'Temperate',  value: parseFloat((p.climate_temperate  ?? 0).toFixed(1)), color: '#5DB89C' },
    { name: 'Cold',       value: parseFloat((p.climate_cold       ?? 0).toFixed(1)), color: '#6B9BC4' },
  ]
  return (
    <div className="rounded-xl p-4 sm:p-6 mb-4 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9B8E7A' }}>
        Climate Performance
      </p>
      {data.map(d => (
        <div key={d.name} className="mb-3">
          <div className="flex justify-between mb-1">
            <span className="text-sm" style={{ color: '#E8DCC8' }}>{d.name}</span>
            <span className="text-sm font-bold" style={{ color: d.color }}>{d.value}/10</span>
          </div>
          <div className="h-1.5 rounded-full" style={{ background: '#1A2035' }}>
            <div className="h-full rounded-full transition-all duration-700"
              style={{ background: d.color, width: `${(d.value / 10) * 100}%` }} />
          </div>
        </div>
      ))}
      <div className="mt-3 px-3 py-2 rounded-lg text-xs" style={{ background: '#1A2035' }}>
        <span style={{ color: '#5A5245' }}>Optimal: </span>
        <span className="font-semibold" style={{ color: '#E8DCC8' }}>
          {p.temp_optimal_min_c?.toFixed(0)}°C – {p.temp_optimal_max_c?.toFixed(0)}°C
        </span>
      </div>
    </div>
  )
}

const CLIMATE_DOT = { tropical: '#C9A84C', arid: '#D4956B', temperate: '#5DB89C', cold: '#6B9BC4' }

function CityGrid({ predictions: p }) {
  const cities = getCityRecommendations(p)
  if (!cities.length) return null

  return (
    <div className="rounded-xl p-4 sm:p-6 mb-4 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-4" style={{ color: '#9B8E7A' }}>
        Recommended Cities · 15 Global Picks
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {cities.map(c => (
          <div
            key={c.id}
            style={{
              background: '#0D1220',
              borderRadius: '10px',
              padding: '12px 14px',
              border: '1px solid rgba(201,168,76,0.10)',
            }}
          >
            {/* City name + country */}
            <div className="flex items-baseline justify-between mb-2">
              <span className="font-semibold text-sm" style={{ color: '#E8DCC8' }}>
                {c.city}
              </span>
              <span className="text-xs ml-2" style={{ color: '#3A3528' }}>{c.country}</span>
            </div>

            {/* Month badges */}
            <div className="flex flex-wrap gap-1 mb-2">
              {c.bestMonths.map(m => (
                <span
                  key={m}
                  style={{
                    background: 'rgba(201,168,76,0.10)',
                    border: '1px solid rgba(201,168,76,0.25)',
                    borderRadius: '999px',
                    padding: '1px 7px',
                    fontSize: '0.63rem',
                    color: '#C9A84C',
                    fontWeight: 600,
                    letterSpacing: '0.02em',
                  }}
                >
                  {m}
                </span>
              ))}
            </div>

            {/* Climate dot + reason */}
            <div className="flex items-start gap-1.5">
              <span
                style={{
                  width: '5px', height: '5px', borderRadius: '50%', flexShrink: 0,
                  background: CLIMATE_DOT[c.climate] || '#8B7355', marginTop: '5px',
                }}
              />
              <p style={{ color: '#4A4235', fontSize: '0.70rem', lineHeight: 1.45, margin: 0 }}>
                {c.reason}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [notFound, setNotFound] = useState(null)  // {similar, requires_notes} when perfume not in DB
  const [lastSearch, setLastSearch] = useState({ name: '', brand: '' })
  const [searchParams] = useSearchParams()

  const defaultName = searchParams.get('name') || ''
  const defaultBrand = searchParams.get('brand') || ''

  const _applyResult = (data) => {
    if (data.not_found) {
      setNotFound(data)
      setResult(null)
    } else {
      setResult(data)
      setNotFound(null)
    }
  }

  const handleSearch = async ({ name, brand, context }) => {
    setLoading(true)
    setError(null)
    setResult(null)
    setNotFound(null)
    setLastSearch({ name, brand: brand || '' })
    try {
      const data = await predictPerfume(name, brand, context)
      _applyResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  const handlePredictFromNotes = async (noteData) => {
    setLoading(true)
    setError(null)
    setNotFound(null)
    try {
      const data = await predictFromNotes(noteData)
      setResult(data)
    } catch (e) {
      setError(e.response?.data?.detail || e.message || 'Prediction failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const name = searchParams.get('name')
    const brand = searchParams.get('brand')
    if (!name) return
    setLoading(true)
    setError(null)
    setResult(null)
    setNotFound(null)
    setLastSearch({ name, brand: brand || '' })
    predictPerfume(name, brand || '', null)
      .then(data => _applyResult(data))
      .catch(e => setError(e.response?.data?.detail || e.message || 'Prediction failed'))
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const p = result?.predictions

  return (
    <div style={PAGE_BG} className="min-h-screen">
      <Particles />
      {/* Hero */}
      <div
        className="px-4 pt-8 pb-6 text-center sm:px-8 sm:pt-12 sm:pb-8"
        style={{ background: 'radial-gradient(ellipse at 50% 0%, rgba(201,168,76,0.05) 0%, transparent 65%)' }}
      >
        <h1
          className="text-3xl sm:text-4xl md:text-5xl font-bold mb-3 tracking-tight"
          style={{ color: '#E8DCC8', fontFamily: "'Playfair Display', Georgia, serif" }}
        >
          Fragrance Intelligence
        </h1>
        <p className="text-sm sm:text-base mb-6 sm:mb-8" style={{ color: '#4A4235' }}>
          Understand what a fragrance does before you buy it.
        </p>
        <PerfumeSearch
          onSearch={handleSearch}
          loading={loading}
          defaultName={defaultName}
          defaultBrand={defaultBrand}
        />
        {error && (
          <p className="mt-4 px-4 py-3 rounded-lg text-sm text-left max-w-2xl mx-auto"
            style={{ color: '#C4614A', background: '#1A0E0E' }}>
            {error}
          </p>
        )}
      </div>

      {/* Not-found panel: shown when perfume isn't in DB */}
      {notFound && (
        <div className="max-w-5xl mx-auto px-4 sm:px-6 md:px-8">
          <OutOfDBPanel
            name={lastSearch.name}
            brand={lastSearch.brand}
            similar={notFound.similar || []}
            onSelectSimilar={(name, brand) => handleSearch({ name, brand, context: null })}
            onPredictFromNotes={handlePredictFromNotes}
            loading={loading}
          />
        </div>
      )}

      {result && p && (
        <div className="max-w-5xl mx-auto px-4 pb-16 sm:px-6 md:px-8">

          {/* Identity Card */}
          <div style={PERFUME_CARD_STYLE} className="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-6 p-4 sm:p-6 mb-6 glass-card">
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold mb-0.5" style={{ color: '#C9A84C' }}>
                {result.perfume.brand}
              </div>
              <div
                className="text-2xl sm:text-3xl font-bold leading-tight break-words"
                style={{ color: '#E8DCC8', fontFamily: "'Playfair Display', Georgia, serif" }}
              >
                {result.perfume.name}
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-1.5">
                <span className="text-xs" style={{ color: '#5A5245' }}>
                  {result.perfume.concentration}
                </span>
                <GenderBadge genderVote={result.perfume.gender_vote} />
                <NLPConclusion
                  confidenceScore={p.confidence_score}
                  modelVersion={p.model_version}
                />
              </div>
              <FamilyChips familyFeatures={p.family_features} />
            </div>
            <div className="flex-shrink-0">
              {(result.perfume.accords || []).map(a => (
                <span key={a} style={ACCORD_BADGE}>{a}</span>
              ))}
            </div>
          </div>

          {/* AI-inferred banner — shown only when source is ai_inferred */}
          {result.source === 'ai_inferred' && (
            <>
              <div
                className="flex items-center gap-3 px-4 py-2.5 rounded-xl mb-4"
                style={{ background: 'rgba(201,168,76,0.07)', border: '1px solid rgba(201,168,76,0.2)' }}
              >
                <span
                  className="text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded"
                  style={{ background: 'rgba(201,168,76,0.15)', color: '#C9A84C', border: '1px solid rgba(201,168,76,0.35)' }}
                >
                  AI-inferred
                </span>
                <span className="text-xs" style={{ color: '#9B8E7A' }}>
                  Notes inferred by AI · confidence:{' '}
                  <span style={{ color: '#C9A84C', fontWeight: 600 }}>
                    {result.inferred_notes?.ai_confidence || 'unknown'}
                  </span>
                  {' '}· not in database
                </span>
              </div>

              {result.inferred_notes && (
                <details className="mb-4">
                  <summary
                    className="flex items-center justify-between cursor-pointer select-none px-4 py-3 rounded-xl text-xs font-bold uppercase tracking-widest"
                    style={{ background: '#0D1117', color: '#4A4235', border: '1px solid rgba(201,168,76,0.10)', listStyle: 'none' }}
                  >
                    <span>Inferred note pyramid</span>
                    <span style={{ fontSize: '0.65rem', opacity: 0.5 }}>expand</span>
                  </summary>
                  <div
                    className="mt-2 px-4 py-3 rounded-xl grid grid-cols-1 sm:grid-cols-3 gap-3"
                    style={{ background: '#0D1117', border: '1px solid rgba(201,168,76,0.08)' }}
                  >
                    {[
                      { label: 'Top', notes: result.inferred_notes.top_notes, color: '#D4B86A' },
                      { label: 'Heart', notes: result.inferred_notes.middle_notes, color: '#C9A84C' },
                      { label: 'Base', notes: result.inferred_notes.base_notes, color: '#8B6914' },
                    ].map(({ label, notes, color }) => (
                      <div key={label}>
                        <p className="text-xs font-bold uppercase tracking-wider mb-1.5" style={{ color }}>{label}</p>
                        <div className="flex flex-wrap gap-1">
                          {(notes || []).map(n => (
                            <span
                              key={n}
                              className="px-2 py-0.5 rounded-full text-xs"
                              style={{ background: `${color}15`, border: `1px solid ${color}35`, color: '#E8DCC8' }}
                            >
                              {n}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </>
          )}

          {/* User-notes banner */}
          {result.source === 'user_notes' && (
            <div
              className="flex items-center gap-3 px-4 py-2.5 rounded-xl mb-4"
              style={{ background: 'rgba(93,184,156,0.07)', border: '1px solid rgba(93,184,156,0.2)' }}
            >
              <span
                className="text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded"
                style={{ background: 'rgba(93,184,156,0.15)', color: '#5DB89C', border: '1px solid rgba(93,184,156,0.35)' }}
              >
                From your notes
              </span>
              <span className="text-xs" style={{ color: '#9B8E7A' }}>
                Prediction built from manually entered notes
              </span>
            </div>
          )}

          {/* Headline Trio */}
          <div className="grid grid-cols-3 gap-3 sm:gap-4 md:gap-5 mb-3">
            <HeadlineScore
              label="Longevity"
              value={`${p.longevity_hours?.toFixed(1)}h`}
              sub="on skin"
              color="#C9A84C"
            />
            <HeadlineScore
              label="Sillage"
              value={p.sillage_score?.toFixed(1)}
              sub="projection"
              color={scoreColor(p.sillage_score)}
            />
            <HeadlineScore
              label="Blind Buy"
              value={p.blind_buy_score?.toFixed(1)}
              sub="would recommend?"
              color={scoreColor(p.blind_buy_score)}
            />
          </div>

          {/* Best worn sentence */}
          <p className="text-sm italic text-center mb-4" style={{ color: '#4A4235' }}>
            {bestWornSentence(p)}
          </p>

          {/* Compact 5-card grid */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-6">
            <ScoreCard label="Versatility"  value={p.versatility_score?.toFixed(1)}  sub="/10" color="#8B7355" />
            <ScoreCard label="Compliment"   value={p.compliment_score?.toFixed(1)}   sub="/10" color="#8B7355" />
            <ScoreCard label="Cost / Wear"  value={p.cost_per_wear_score?.toFixed(1)} sub="/10" color="#8B7355" />
            <ScoreCard
              label="Temp range"
              value={`${p.temp_optimal_min_c?.toFixed(0)}°–${p.temp_optimal_max_c?.toFixed(0)}°C`}
              sub=""
              color="#8B7355"
            />
            <ScoreCard
              label="Peaks at"
              value={`${p.performance_peak_hour?.toFixed(1)}h`}
              sub="after application"
              color="#8B7355"
            />
          </div>

          <SectionDivider label="Fragrance DNA" />

          {/* Family Radar + Context Heatmap */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 md:gap-5 mb-6">
            <FamilyRadar familyFeatures={p.family_features} />
            <ContextHeatmap predictions={p} />
          </div>

          <SectionDivider label="Performance" />

          {/* Longevity Decay + Time of Day */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 md:gap-5 mb-6">
            <LongevityDecayChart predictions={p} />
            <TimeOfDayChart predictions={p} />
          </div>

          {/* Person fit top-picks row */}
          <PersonFitBadges predictions={p} />

          {/* ── Collapsible sections ─────────────────────────────────────────── */}

          <CollapsibleSection label="Season & Occasion Details">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 mb-4">
              <SeasonBars predictions={p} />
              <OccasionRanking predictions={p} />
            </div>
          </CollapsibleSection>

          <CollapsibleSection label="Climate & Cities">
            <ClimateChart predictions={p} />
            <CityGrid predictions={p} />
          </CollapsibleSection>

          <CollapsibleSection label="Full Person Fit & Distribution">
            <FullPersonFit predictions={p} />
            <PieChart predictions={p} />
          </CollapsibleSection>

        </div>
      )}
    </div>
  )
}
