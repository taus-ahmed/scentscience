import React, { useState } from 'react'
import PerfumeSearch from '../components/PerfumeSearch.jsx'
import ScoreCard from '../components/ScoreCard.jsx'
import RadarChart from '../components/RadarChart.jsx'
import BarChart from '../components/BarChart.jsx'
import PieChart from '../components/PieChart.jsx'
import NLPConclusion from '../components/NLPConclusion.jsx'
import { predictPerfume } from '../api/client.js'

const s = {
  page: { minHeight: '100vh', background: 'linear-gradient(180deg, #0a0a0f 0%, #0f0f1f 100%)' },
  hero: { padding: '3rem 2rem 2rem', textAlign: 'center' },
  title: { fontSize: '2.8rem', fontWeight: 900, color: '#fff', letterSpacing: '-1px', marginBottom: '0.5rem' },
  sub: { color: '#6b7280', fontSize: '1rem', marginBottom: '2.5rem' },
  badge: {
    display: 'inline-block', padding: '0.25rem 0.75rem', borderRadius: '999px',
    background: '#1e1b4b', color: '#a78bfa', fontSize: '0.75rem', fontWeight: 600,
    marginRight: '0.5rem', marginBottom: '2rem',
  },
  content: { maxWidth: '1200px', margin: '0 auto', padding: '0 2rem 4rem' },
  perfumeCard: {
    background: 'linear-gradient(135deg, #1e1b4b 0%, #1a1a3e 100%)',
    borderRadius: '16px', padding: '1.5rem 2rem',
    border: '1px solid #312e81', marginBottom: '2rem',
    display: 'flex', alignItems: 'center', gap: '2rem', flexWrap: 'wrap',
  },
  perfumeName: { fontSize: '2rem', fontWeight: 800, color: '#fff' },
  perfumeBrand: { color: '#a78bfa', fontSize: '1rem', fontWeight: 600 },
  accordBadge: {
    display: 'inline-block', padding: '0.2rem 0.6rem',
    background: '#312e81', borderRadius: '999px',
    fontSize: '0.72rem', color: '#c4b5fd', marginRight: '0.4rem',
  },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '2rem' },
  chartsGrid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '2rem' },
  sectionTitle: { fontSize: '1rem', fontWeight: 700, color: '#94a3b8', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' },
  error: { color: '#f87171', background: '#1c1c2e', padding: '1rem', borderRadius: '8px', marginTop: '1rem' },
}

export default function Dashboard() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

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

  const p = result?.predictions

  return (
    <div style={s.page}>
      <div style={s.hero}>
        <h1 style={s.title}>Fragrance Intelligence</h1>
        <p style={s.sub}>ML-powered prediction engine — 35+ performance outputs from a single perfume</p>
        <span style={s.badge}>XGBoost Model</span>
        <span style={s.badge}>Claude NLP</span>
        <span style={s.badge}>35+ Predictions</span>
        <PerfumeSearch onSearch={handleSearch} loading={loading} />
        {error && <p style={s.error}>{error}</p>}
      </div>

      {result && p && (
        <div style={s.content}>
          {/* Perfume Identity Card */}
          <div style={s.perfumeCard}>
            <div>
              <div style={s.perfumeBrand}>{result.perfume.brand}</div>
              <div style={s.perfumeName}>{result.perfume.name}</div>
              <div style={{ color: '#6b7280', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                {result.perfume.concentration}
              </div>
            </div>
            <div>
              {(result.perfume.accords || []).map(a => (
                <span key={a} style={s.accordBadge}>{a}</span>
              ))}
            </div>
          </div>

          {/* Score Cards */}
          <p style={s.sectionTitle}>Key Metrics</p>
          <div style={s.grid}>
            <ScoreCard label="Longevity" value={`${p.longevity_hours?.toFixed(1)}h`} sub="on skin" color="#a78bfa" />
            <ScoreCard label="Sillage" value={p.sillage_score?.toFixed(1)} sub="/10" color="#34d399" />
            <ScoreCard label="Versatility" value={p.versatility_score?.toFixed(1)} sub="/10" color="#60a5fa" />
            <ScoreCard label="Blind Buy" value={p.blind_buy_score?.toFixed(1)} sub="/10" color="#fbbf24" />
            <ScoreCard label="Compliment" value={p.compliment_score?.toFixed(1)} sub="/10" color="#f472b6" />
            <ScoreCard label="Cost/Wear" value={p.cost_per_wear_score?.toFixed(1)} sub="/10" color="#fb923c" />
            <ScoreCard label="Projection 1h" value={p.proj_1hr?.toFixed(1)} sub="/10" color="#e879f9" />
            <ScoreCard label="Heat Performance" value={p.heat_amplification?.toFixed(1)} sub="/10" color="#f87171" />
          </div>

          {/* Charts */}
          <p style={s.sectionTitle}>Performance Charts</p>
          <div style={s.chartsGrid}>
            <RadarChart predictions={p} />
            <BarChart predictions={p} />
          </div>
          <div style={s.chartsGrid}>
            <PieChart predictions={p} />
            <ClimateChart predictions={p} />
          </div>

          {/* Person Fit */}
          <PersonFit predictions={p} />

          {/* NLP Conclusion */}
          <NLPConclusion
            conclusion={p.nlp_conclusion}
            instagramBrief={p.instagram_brief}
            perfumeName={`${result.perfume.brand} ${result.perfume.name}`}
          />
        </div>
      )}
    </div>
  )
}

function ClimateChart({ predictions: p }) {
  const data = [
    { name: 'Tropical', value: parseFloat(p.climate_tropical?.toFixed(1)), color: '#f59e0b' },
    { name: 'Arid', value: parseFloat(p.climate_arid?.toFixed(1)), color: '#fb923c' },
    { name: 'Temperate', value: parseFloat(p.climate_temperate?.toFixed(1)), color: '#34d399' },
    { name: 'Cold', value: parseFloat(p.climate_cold?.toFixed(1)), color: '#60a5fa' },
  ]
  return (
    <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid #1f2937' }}>
      <p style={{ color: '#9ca3af', fontSize: '0.8rem', fontWeight: 700, marginBottom: '1rem', textTransform: 'uppercase' }}>Climate Performance</p>
      {data.map(d => (
        <div key={d.name} style={{ marginBottom: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
            <span style={{ color: '#d1d5db', fontSize: '0.85rem' }}>{d.name}</span>
            <span style={{ color: d.color, fontWeight: 700, fontSize: '0.85rem' }}>{d.value}/10</span>
          </div>
          <div style={{ background: '#1f2937', borderRadius: '999px', height: '6px' }}>
            <div style={{ background: d.color, width: `${(d.value / 10) * 100}%`, height: '100%', borderRadius: '999px', transition: 'width 0.8s ease' }} />
          </div>
        </div>
      ))}
      <div style={{ marginTop: '1rem', padding: '0.75rem', background: '#1f2937', borderRadius: '8px' }}>
        <span style={{ color: '#6b7280', fontSize: '0.78rem' }}>Optimal: </span>
        <span style={{ color: '#e5e7eb', fontSize: '0.78rem', fontWeight: 600 }}>
          {p.temp_optimal_min_c?.toFixed(0)}°C – {p.temp_optimal_max_c?.toFixed(0)}°C
        </span>
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

  const s2 = {
    section: { background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid #1f2937', marginBottom: '2rem' },
    title: { color: '#9ca3af', fontSize: '0.8rem', fontWeight: 700, marginBottom: '1.25rem', textTransform: 'uppercase' },
    grid3: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem' },
    barRow: { marginBottom: '0.6rem' },
    barLabel: { display: 'flex', justifyContent: 'space-between', marginBottom: '0.2rem' },
    barLabelText: { color: '#d1d5db', fontSize: '0.8rem' },
    barVal: { fontWeight: 700, fontSize: '0.8rem' },
    barBg: { background: '#1f2937', borderRadius: '999px', height: '5px' },
  }

  const Bar = ({ label, value, color = '#a78bfa' }) => (
    <div style={s2.barRow}>
      <div style={s2.barLabel}>
        <span style={s2.barLabelText}>{label}</span>
        <span style={{ ...s2.barVal, color }}>{value?.toFixed(1)}</span>
      </div>
      <div style={s2.barBg}>
        <div style={{ background: color, width: `${(value / 10) * 100}%`, height: '100%', borderRadius: '999px' }} />
      </div>
    </div>
  )

  return (
    <div style={s2.section}>
      <p style={s2.title}>Person Fit Analysis</p>
      <div style={s2.grid3}>
        <div>
          <p style={{ color: '#6b7280', fontSize: '0.75rem', marginBottom: '0.75rem' }}>SKIN TYPE</p>
          {skinData.map(d => <Bar key={d.label} {...d} />)}
        </div>
        <div>
          <p style={{ color: '#6b7280', fontSize: '0.75rem', marginBottom: '0.75rem' }}>AGE BRACKET</p>
          {ageData.map(d => <Bar key={d.label} {...d} color="#fbbf24" />)}
        </div>
        <div>
          <p style={{ color: '#6b7280', fontSize: '0.75rem', marginBottom: '0.75rem' }}>PERSONALITY</p>
          {personData.map(d => <Bar key={d.label} {...d} />)}
        </div>
      </div>
    </div>
  )
}
