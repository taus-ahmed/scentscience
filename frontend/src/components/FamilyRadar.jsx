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
  background: '#1f2937', border: '1px solid #374151',
  borderRadius: '8px', color: '#e5e7eb',
}

export default function FamilyRadar({ familyFeatures }) {
  if (!familyFeatures || typeof familyFeatures !== 'object') return null

  const data = FAMILY_NAMES
    .map(f => ({ subject: f[0].toUpperCase() + f.slice(1), value: familyFeatures[f] || 0 }))
    .filter(d => d.value > 0.01)

  if (data.length < 3) return null

  return (
    <div className="rounded-xl p-4 sm:p-6" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9ca3af' }}>
        Note Family DNA
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <ReRadarChart cx="50%" cy="50%" outerRadius="72%" data={data}>
          <PolarGrid stroke="#1f2937" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#6b7280', fontSize: 10 }} />
          <PolarRadiusAxis angle={90} domain={[0, 1]} tick={false} axisLine={false} />
          <Radar
            name="Family"
            dataKey="value"
            stroke="#6366f1"
            fill="#6366f1"
            fillOpacity={0.25}
            strokeWidth={2}
          />
          <Tooltip
            contentStyle={TIP_STYLE}
            formatter={v => [(v * 100).toFixed(0) + '%', 'Weight']}
          />
        </ReRadarChart>
      </ResponsiveContainer>
    </div>
  )
}
