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
import { predictPerfume } from '../api/client.js'

const PAGE_BG = { background: 'linear-gradient(180deg, #0a0a0f 0%, #0f0f1f 100%)' }

const PERFUME_CARD_STYLE = {
  background: 'linear-gradient(135deg, #1e1b4b 0%, #1a1a3e 100%)',
  borderRadius: '16px', border: '1px solid #312e81',
}
const ACCORD_BADGE = {
  display: 'inline-block', padding: '0.2rem 0.6rem',
  background: '#312e81', borderRadius: '999px',
  fontSize: '0.72rem', color: '#c4b5fd',
  marginRight: '0.4rem', marginBottom: '0.3rem',
}

const FAMILY_COLORS = {
  citrus: '#f59e0b', woody: '#b45309', floral: '#f472b6',
  oriental: '#a78bfa', fresh: '#2dd4bf', gourmand: '#fb923c',
  chypre: '#84cc16', fougere: '#22d3ee', aquatic: '#60a5fa',
  spicy: '#ef4444', earthy: '#4ade80', green: '#86efac',
  powdery: '#c4b5fd', smoky: '#9ca3af', resinous: '#d97706',
  musky: '#fda4af', animalic: '#78350f',
}

const OCC_LABELS = {
  occ_office: 'office', occ_date: 'date nights', occ_casual: 'casual',
  occ_formal: 'formal', occ_sport: 'sport', occ_travel: 'travel',
}

function scoreColor(v) {
  if (v == null || isNaN(v)) return '#a78bfa'
  if (v > 7) return '#34d399'
  if (v >= 4) return '#fbbf24'
  return '#ef4444'
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
      className="flex flex-col items-center text-center p-4 sm:p-6 rounded-2xl"
      style={{ background: '#111827', border: `1px solid ${color}25` }}
    >
      <span className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: '#4b5563' }}>
        {label}
      </span>
      <span className="text-4xl sm:text-5xl font-black leading-none mb-1.5" style={{ color }}>
        {value}
      </span>
      <span className="text-xs" style={{ color: '#374151' }}>{sub}</span>
    </div>
  )
}

function SectionDivider({ label }) {
  return (
    <div className="flex items-center gap-3 my-6">
      <div className="flex-1 h-px" style={{ background: '#1f2937' }} />
      {label && (
        <span className="text-xs font-bold uppercase tracking-widest" style={{ color: '#374151' }}>
          {label}
        </span>
      )}
      <div className="flex-1 h-px" style={{ background: '#1f2937' }} />
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
        const c = FAMILY_COLORS[fam] || '#6b7280'
        return (
          <span
            key={fam}
            style={{
              padding: '0.15rem 0.55rem', borderRadius: '999px',
              fontSize: '0.7rem', background: `${c}1a`,
              border: `1px solid ${c}55`, color: c,
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
          style={{ background: '#111827', border: '1px solid #1f2937' }}
        >
          <span style={{ color: '#4b5563' }}>{label}:</span>
          <span className="font-semibold" style={{ color: '#9ca3af' }}>{best}</span>
        </div>
      ))}
    </div>
  )
}

function CollapsibleSection({ label, children }) {
  return (
    <details className="mb-3">
      <summary
        className="flex items-center justify-between cursor-pointer select-none px-4 py-3 rounded-xl text-xs font-bold uppercase tracking-widest"
        style={{ background: '#0d1117', color: '#374151', border: '1px solid #1a1a2e', listStyle: 'none' }}
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
    { label: 'Dry Skin',   value: p.skin_dry_score,  color: '#a78bfa' },
    { label: 'Oily Skin',  value: p.skin_oily_score,  color: '#34d399' },
    { label: 'Combo Skin', value: p.skin_combo_score, color: '#60a5fa' },
  ]
  const ageData = [
    { label: '18–25', value: p.age_18_25 },
    { label: '25–35', value: p.age_25_35 },
    { label: '35–50', value: p.age_35_50 },
    { label: '50+',   value: p.age_50_plus },
  ]
  const personData = [
    { label: 'Dominant',     value: p.personality_dominant,     color: '#f87171' },
    { label: 'Intellectual', value: p.personality_intellectual, color: '#60a5fa' },
    { label: 'Casual',       value: p.personality_casual,       color: '#34d399' },
    { label: 'Romantic',     value: p.personality_romantic,     color: '#f472b6' },
  ]
  const genderData = [
    { label: 'Masculine', value: p.gender_masculine, color: '#60a5fa' },
    { label: 'Feminine',  value: p.gender_feminine,  color: '#f472b6' },
    { label: 'Unisex',    value: p.gender_unisex,    color: '#34d399' },
  ]

  const Bar = ({ label, value, color = '#a78bfa' }) => (
    <div className="mb-2.5">
      <div className="flex justify-between mb-1">
        <span className="text-xs" style={{ color: '#d1d5db' }}>{label}</span>
        <span className="text-xs font-bold" style={{ color }}>{value?.toFixed(1)}</span>
      </div>
      <div className="h-1 rounded-full" style={{ background: '#1f2937' }}>
        <div className="h-full rounded-full" style={{ background: color, width: `${((value ?? 0) / 10) * 100}%` }} />
      </div>
    </div>
  )

  return (
    <div className="rounded-xl p-4 sm:p-6 mb-4" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#6b7280' }}>Skin Type</p>
          {skinData.map(d => <Bar key={d.label} {...d} />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#6b7280' }}>Age Bracket</p>
          {ageData.map(d => <Bar key={d.label} {...d} color="#fbbf24" />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#6b7280' }}>Personality</p>
          {personData.map(d => <Bar key={d.label} {...d} />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#6b7280' }}>Gender Expression</p>
          {genderData.map(d => <Bar key={d.label} {...d} />)}
        </div>
      </div>
    </div>
  )
}

function ClimateChart({ predictions: p }) {
  const data = [
    { name: 'Tropical',   value: parseFloat((p.climate_tropical  ?? 0).toFixed(1)), color: '#f59e0b' },
    { name: 'Arid',       value: parseFloat((p.climate_arid       ?? 0).toFixed(1)), color: '#fb923c' },
    { name: 'Temperate',  value: parseFloat((p.climate_temperate  ?? 0).toFixed(1)), color: '#34d399' },
    { name: 'Cold',       value: parseFloat((p.climate_cold       ?? 0).toFixed(1)), color: '#60a5fa' },
  ]
  return (
    <div className="rounded-xl p-4 sm:p-6 mb-4" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9ca3af' }}>
        Climate Performance
      </p>
      {data.map(d => (
        <div key={d.name} className="mb-3">
          <div className="flex justify-between mb-1">
            <span className="text-sm" style={{ color: '#d1d5db' }}>{d.name}</span>
            <span className="text-sm font-bold" style={{ color: d.color }}>{d.value}/10</span>
          </div>
          <div className="h-1.5 rounded-full" style={{ background: '#1f2937' }}>
            <div className="h-full rounded-full transition-all duration-700"
              style={{ background: d.color, width: `${(d.value / 10) * 100}%` }} />
          </div>
        </div>
      ))}
      <div className="mt-3 px-3 py-2 rounded-lg text-xs" style={{ background: '#1f2937' }}>
        <span style={{ color: '#6b7280' }}>Optimal: </span>
        <span className="font-semibold" style={{ color: '#e5e7eb' }}>
          {p.temp_optimal_min_c?.toFixed(0)}°C – {p.temp_optimal_max_c?.toFixed(0)}°C
        </span>
      </div>
    </div>
  )
}

function GeoSection({ predictions: p }) {
  const sections = [
    { key: 'geo_tropical_cities',  label: 'Tropical',  color: '#f59e0b' },
    { key: 'geo_arid_cities',      label: 'Arid',      color: '#fb923c' },
    { key: 'geo_temperate_cities', label: 'Temperate', color: '#34d399' },
    { key: 'geo_cold_cities',      label: 'Cold',      color: '#60a5fa' },
  ]
  const hasAny = sections.some(sec => (p[sec.key] || []).length > 0)
  if (!hasAny) return null

  return (
    <div className="rounded-xl p-4 sm:p-6 mb-4" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9ca3af' }}>
        Recommended Cities
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {sections.map(({ key, label, color }) => {
          const cities = p[key] || []
          if (!cities.length) return null
          return (
            <div key={key}>
              <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color }}>{label}</p>
              <div className="flex flex-wrap gap-1.5">
                {cities.map(city => (
                  <span
                    key={city}
                    className="px-2 py-0.5 rounded-full text-xs"
                    style={{ background: `${color}18`, border: `1px solid ${color}40`, color: '#d1d5db' }}
                  >
                    {city}
                  </span>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function Dashboard() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [searchParams] = useSearchParams()

  const handleSearch = async ({ name, brand, context }) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await predictPerfume(name, brand, context)
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
    predictPerfume(name, brand || '', null)
      .then(data => setResult(data))
      .catch(e => setError(e.response?.data?.detail || e.message || 'Prediction failed'))
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const p = result?.predictions
  const defaultName = searchParams.get('name') || ''
  const defaultBrand = searchParams.get('brand') || ''

  return (
    <div style={PAGE_BG} className="min-h-screen">
      {/* Hero — simplified */}
      <div className="px-4 pt-8 pb-6 text-center sm:px-8 sm:pt-12 sm:pb-8">
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-3 tracking-tight">
          Fragrance Intelligence
        </h1>
        <p className="text-sm sm:text-base mb-6 sm:mb-8" style={{ color: '#4b5563' }}>
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
            style={{ color: '#f87171', background: '#1c1c2e' }}>
            {error}
          </p>
        )}
      </div>

      {result && p && (
        <div className="max-w-5xl mx-auto px-4 pb-16 sm:px-6 md:px-8">

          {/* Identity Card */}
          <div style={PERFUME_CARD_STYLE} className="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-6 p-4 sm:p-6 mb-6">
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold mb-0.5" style={{ color: '#a78bfa' }}>
                {result.perfume.brand}
              </div>
              <div className="text-2xl sm:text-3xl font-black text-white leading-tight break-words">
                {result.perfume.name}
              </div>
              <div className="text-xs mt-0.5" style={{ color: '#6b7280' }}>
                {result.perfume.concentration}
              </div>
              <FamilyChips familyFeatures={p.family_features} />
            </div>
            <div className="flex-shrink-0">
              {(result.perfume.accords || []).map(a => (
                <span key={a} style={ACCORD_BADGE}>{a}</span>
              ))}
            </div>
          </div>

          {/* Headline Trio */}
          <div className="grid grid-cols-3 gap-3 sm:gap-4 md:gap-5 mb-3">
            <HeadlineScore
              label="Longevity"
              value={`${p.longevity_hours?.toFixed(1)}h`}
              sub="on skin"
              color="#a78bfa"
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
          <p className="text-sm italic text-center mb-4" style={{ color: '#4b5563' }}>
            {bestWornSentence(p)}
          </p>

          {/* Compact 5-card grid */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-6">
            <ScoreCard label="Versatility"  value={p.versatility_score?.toFixed(1)}  sub="/10" color="#6b7280" />
            <ScoreCard label="Compliment"   value={p.compliment_score?.toFixed(1)}   sub="/10" color="#6b7280" />
            <ScoreCard label="Cost / Wear"  value={p.cost_per_wear_score?.toFixed(1)} sub="/10" color="#6b7280" />
            <ScoreCard
              label="Temp range"
              value={`${p.temp_optimal_min_c?.toFixed(0)}°–${p.temp_optimal_max_c?.toFixed(0)}°C`}
              sub=""
              color="#6b7280"
            />
            <ScoreCard
              label="Peaks at"
              value={`${p.performance_peak_hour?.toFixed(1)}h`}
              sub="after application"
              color="#6b7280"
            />
          </div>

          <SectionDivider />

          {/* NLP Conclusion — moved above charts */}
          <NLPConclusion
            conclusion={p.nlp_conclusion}
            instagramBrief={p.instagram_brief}
            perfumeName={`${result.perfume.brand} ${result.perfume.name}`}
            confidenceScore={p.confidence_score}
            modelVersion={p.model_version}
          />

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
            <GeoSection predictions={p} />
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
