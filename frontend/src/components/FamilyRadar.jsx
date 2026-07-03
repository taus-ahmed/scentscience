import React from 'react'
import {
  Radar, RadarChart as ReRadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip,
} from 'recharts'

const FAMILY_NAMES = [
  'citrus', 'woody', 'floral', 'oriental', 'fresh', 'gourmand',
  'chypre', 'fougere', 'aquatic', 'spicy', 'earthy', 'green',
  'powdery', 'smoky', 'resinous', 'musky', 'animalic',
]

const TIP_STYLE = {
  background: '#141A2E', border: '1px solid rgba(201,168,76,0.2)',
  borderRadius: '8px', color: '#E8DCC8',
}

export default function FamilyRadar({ familyFeatures }) {
  if (!familyFeatures || typeof familyFeatures !== 'object') return null

  const data = FAMILY_NAMES.map(f => ({
    subject: f[0].toUpperCase() + f.slice(1),
    value: Math.round((familyFeatures[f] || 0) * 100),
    fullMark: 100,
  }))

  if (data.every(d => d.value === 0)) return null

  return (
    <div className="rounded-xl p-4 sm:p-6 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9B8E7A' }}>
        Note Family DNA
      </p>
      <ResponsiveContainer width="100%" height={380}>
        <ReRadarChart cx="50%" cy="50%" outerRadius="42%" data={data}>
          <PolarGrid stroke="#1A2035" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#5A5245', fontSize: 10 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar
            name="Family"
            dataKey="value"
            stroke="#C9A84C"
            fill="#C9A84C"
            fillOpacity={0.18}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={TIP_STYLE}
            formatter={v => [v + '%', 'Weight']}
          />
        </ReRadarChart>
      </ResponsiveContainer>
    </div>
  )
}
