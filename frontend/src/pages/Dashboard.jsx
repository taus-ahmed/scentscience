import React, { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import PerfumeSearch from '../components/PerfumeSearch.jsx'
import ScoreCard from '../components/ScoreCard.jsx'
import RadarChart from '../components/RadarChart.jsx'
import BarChart from '../components/BarChart.jsx'
import PieChart from '../components/PieChart.jsx'
import NLPConclusion from '../components/NLPConclusion.jsx'
import { predictPerfume } from '../api/client.js'

const PAGE_BG = { background: 'linear-gradient(180deg, #0a0a0f 0%, #0f0f1f 100%)' }
const BADGE_STYLE = {
  display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '999px',
  background: '#1e1b4b', color: '#a78bfa', fontSize: '0.75rem', fontWeight: 600,
  marginRight: '0.5rem', marginBottom: '0.5rem',
}
const PERFUME_CARD_STYLE = {
  background: 'linear-gradient(135deg, #1e1b4b 0%, #1a1a3e 100%)',
  borderRadius: '16px', border: '1px solid #312e81',
}
const ACCORD_BADGE = {
  display: 'inline-block', padding: '0.2rem 0.6rem',
  background: '#312e81', borderRadius: '999px',
  fontSize: '0.72rem', color: '#c4b5fd', marginRight: '0.4rem', marginBottom: '0.3rem',
}

const scoreColor = (v) => {
  if (v == null || isNaN(v)) return '#a78bfa'
  if (v > 7) return '#34d399'
  if (v >= 4) return '#fbbf24'
  return '#ef4444'
}

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
      {/* Hero */}
      <div className="px-4 pt-8 pb-6 text-center sm:px-8 sm:pt-12 sm:pb-8">
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-black text-white mb-2 tracking-tight">
          Fragrance Intelligence
        </h1>
        <p className="text-sm sm:text-base mb-6 sm:mb-8" style={{ color: '#6b7280' }}>
          ML-powered prediction engine — 35+ performance outputs from a single perfume
        </p>
        <div className="mb-4 sm:mb-6">
          <span style={BADGE_STYLE}>XGBoost Model</span>
          <span style={BADGE_STYLE}>Claude NLP</span>
          <span style={BADGE_STYLE}>35+ Predictions</span>
        </div>
        <PerfumeSearch
          onSearch={handleSearch}
          loading={loading}
          defaultName={defaultName}
          defaultBrand={defaultBrand}
        />
        {error && (
          <p className="mt-4 px-4 py-3 rounded-lg text-sm text-left max-w-2xl mx-auto" style={{ color: '#f87171', background: '#1c1c2e' }}>
            {error}
          </p>
        )}
      </div>

      {result && p && (
        <div className="max-w-6xl mx-auto px-4 pb-16 sm:px-6 md:px-8">

          {/* Perfume Identity Card */}
          <div style={PERFUME_CARD_STYLE} className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-8 p-4 sm:p-6 mb-6 sm:mb-8">
            <div className="min-w-0 flex-1">
              <div className="text-sm font-semibold mb-0.5" style={{ color: '#a78bfa' }}>
                {result.perfume.brand}
              </div>
              <div className="text-2xl sm:text-3xl font-black text-white leading-tight break-words">
                {result.perfume.name}
              </div>
              <div className="text-xs mt-1" style={{ color: '#6b7280' }}>
                {result.perfume.concentration}
              </div>
            </div>
            <div className="flex-shrink-0">
              {(result.perfume.accords || []).map(a => (
                <span key={a} style={ACCORD_BADGE}>{a}</span>
              ))}
            </div>
          </div>

          {/* Score Cards — 2 cols mobile, 4 cols desktop */}
          <p className="text-xs font-bold uppercase tracking-widest mb-3 sm:mb-4" style={{ color: '#94a3b8' }}>
            Key Metrics
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3 md:gap-4 mb-6 sm:mb-8">
            <ScoreCard label="Longevity" value={`${p.longevity_hours?.toFixed(1)}h`} sub="on skin" color="#a78bfa" />
            <ScoreCard label="Sillage" value={p.sillage_score?.toFixed(1)} sub="/10" color={scoreColor(p.sillage_score)} />
            <ScoreCard label="Versatility" value={p.versatility_score?.toFixed(1)} sub="/10" color={scoreColor(p.versatility_score)} />
            <ScoreCard label="Blind Buy" value={p.blind_buy_score?.toFixed(1)} sub="/10" color={scoreColor(p.blind_buy_score)} />
            <ScoreCard label="Compliment" value={p.compliment_score?.toFixed(1)} sub="/10" color={scoreColor(p.compliment_score)} />
            <ScoreCard label="Cost/Wear" value={p.cost_per_wear_score?.toFixed(1)} sub="/10" color={scoreColor(p.cost_per_wear_score)} />
            <ScoreCard label="Projection 1h" value={p.proj_1hr?.toFixed(1)} sub="/10" color={scoreColor(p.proj_1hr)} />
            <ScoreCard label="Heat Perf." value={p.heat_amplification?.toFixed(1)} sub="/10" color={scoreColor(p.heat_amplification)} />
          </div>

          {/* Charts — 1 col mobile, 2 cols md+ */}
          <p className="text-xs font-bold uppercase tracking-widest mb-3 sm:mb-4" style={{ color: '#94a3b8' }}>
            Performance Charts
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 md:gap-6 mb-3 sm:mb-4 md:mb-6">
            <RadarChart predictions={p} />
            <BarChart predictions={p} />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 md:gap-6 mb-6 sm:mb-8">
            <PieChart predictions={p} />
            <ClimateChart predictions={p} />
          </div>

          {/* Person Fit */}
          <PersonFit predictions={p} />

          {/* Geo Section */}
          <GeoSection predictions={p} />

          {/* NLP Conclusion */}
          <NLPConclusion
            conclusion={p.nlp_conclusion}
            instagramBrief={p.instagram_brief}
            perfumeName={`${result.perfume.brand} ${result.perfume.name}`}
            confidenceScore={p.confidence_score}
            modelVersion={p.model_version}
          />
        </div>
      )}
    </div>
  )
}

function ClimateChart({ predictions: p }) {
  const data = [
    { name: 'Tropical', value: parseFloat((p.climate_tropical ?? 0).toFixed(1)), color: '#f59e0b' },
    { name: 'Arid', value: parseFloat((p.climate_arid ?? 0).toFixed(1)), color: '#fb923c' },
    { name: 'Temperate', value: parseFloat((p.climate_temperate ?? 0).toFixed(1)), color: '#34d399' },
    { name: 'Cold', value: parseFloat((p.climate_cold ?? 0).toFixed(1)), color: '#60a5fa' },
  ]
  return (
    <div className="rounded-xl p-4 sm:p-6" style={{ background: '#111827', border: '1px solid #1f2937' }}>
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
            <div className="h-full rounded-full transition-all duration-700" style={{ background: d.color, width: `${(d.value / 10) * 100}%` }} />
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
    { key: 'geo_tropical_cities', label: 'Tropical', color: '#f59e0b' },
    { key: 'geo_arid_cities', label: 'Arid', color: '#fb923c' },
    { key: 'geo_temperate_cities', label: 'Temperate', color: '#34d399' },
    { key: 'geo_cold_cities', label: 'Cold', color: '#60a5fa' },
  ]
  const hasAny = sections.some(sec => (p[sec.key] || []).length > 0)
  if (!hasAny) return null

  return (
    <div className="rounded-xl p-4 sm:p-6 mb-6 sm:mb-8" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9ca3af' }}>
        Recommended Cities
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {sections.map(({ key, label, color }) => {
          const cities = p[key] || []
          if (!cities.length) return null
          return (
            <div key={key}>
              <p className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color }}>
                {label}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {cities.map(city => (
                  <span key={city} className="px-2 py-0.5 rounded-full text-xs" style={{
                    background: `${color}18`,
                    border: `1px solid ${color}40`,
                    color: '#d1d5db',
                  }}>
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

function PersonFit({ predictions: p }) {
  const skinData = [
    { label: 'Dry Skin', value: p.skin_dry_score, color: '#a78bfa' },
    { label: 'Oily Skin', value: p.skin_oily_score, color: '#34d399' },
    { label: 'Combo Skin', value: p.skin_combo_score, color: '#60a5fa' },
  ]
  const ageData = [
    { label: '18–25', value: p.age_18_25 },
    { label: '25–35', value: p.age_25_35 },
    { label: '35–50', value: p.age_35_50 },
    { label: '50+', value: p.age_50_plus },
  ]
  const personData = [
    { label: 'Dominant', value: p.personality_dominant, color: '#f87171' },
    { label: 'Intellectual', value: p.personality_intellectual, color: '#60a5fa' },
    { label: 'Casual', value: p.personality_casual, color: '#34d399' },
    { label: 'Romantic', value: p.personality_romantic, color: '#f472b6' },
  ]
  const genderData = [
    { label: 'Masculine', value: p.gender_masculine, color: '#60a5fa' },
    { label: 'Feminine', value: p.gender_feminine, color: '#f472b6' },
    { label: 'Unisex', value: p.gender_unisex, color: '#34d399' },
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
    <div className="rounded-xl p-4 sm:p-6 mb-6 sm:mb-8" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-4 sm:mb-5" style={{ color: '#9ca3af' }}>
        Person Fit Analysis
      </p>
      {/* 1 col on mobile, 2 cols on sm, 4 cols on md+ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#6b7280' }}>SKIN TYPE</p>
          {skinData.map(d => <Bar key={d.label} {...d} />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#6b7280' }}>AGE BRACKET</p>
          {ageData.map(d => <Bar key={d.label} {...d} color="#fbbf24" />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#6b7280' }}>PERSONALITY</p>
          {personData.map(d => <Bar key={d.label} {...d} />)}
        </div>
        <div>
          <p className="text-xs uppercase tracking-wider mb-2.5" style={{ color: '#6b7280' }}>GENDER EXPRESSION</p>
          {genderData.map(d => <Bar key={d.label} {...d} />)}
        </div>
      </div>
    </div>
  )
}
