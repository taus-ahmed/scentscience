import React from 'react'
import {
  Radar, RadarChart as ReRadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip
} from 'recharts'

export default function RadarChart({ predictions: p }) {
  const data = [
    { subject: 'Spring', value: p.season_spring },
    { subject: 'Summer', value: p.season_summer },
    { subject: 'Fall', value: p.season_fall },
    { subject: 'Winter', value: p.season_winter },
    { subject: 'Office', value: p.occ_office },
    { subject: 'Date', value: p.occ_date },
    { subject: 'Casual', value: p.occ_casual },
    { subject: 'Formal', value: p.occ_formal },
    { subject: 'Sport', value: p.occ_sport },
    { subject: 'Travel', value: p.occ_travel },
  ]

  return (
    <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid #1f2937' }}>
      <p style={{ color: '#9ca3af', fontSize: '0.8rem', fontWeight: 700, marginBottom: '1rem', textTransform: 'uppercase' }}>
        Season & Occasion Fit
      </p>
      <ResponsiveContainer width="100%" height={280}>
        <ReRadarChart cx="50%" cy="50%" outerRadius="75%" data={data}>
          <PolarGrid stroke="#1f2937" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: '#6b7280', fontSize: 11 }} />
          <PolarRadiusAxis angle={90} domain={[0, 10]} tick={false} axisLine={false} />
          <Radar name="Score" dataKey="value" stroke="#a78bfa" fill="#a78bfa" fillOpacity={0.25} strokeWidth={2} />
          <Tooltip
            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#e5e7eb' }}
            formatter={v => [v?.toFixed(1), 'Score']}
          />
        </ReRadarChart>
      </ResponsiveContainer>
    </div>
  )
}
