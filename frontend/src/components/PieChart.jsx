import React from 'react'
import { PieChart as RePieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const GENDER_COLORS = ['#60a5fa', '#f472b6', '#34d399']
const SKIN_COLORS = ['#a78bfa', '#fb923c', '#34d399']

export default function PieChart({ predictions: p }) {
  const genderData = [
    { name: 'Masculine', value: parseFloat(p.gender_masculine?.toFixed(1)) },
    { name: 'Feminine', value: parseFloat(p.gender_feminine?.toFixed(1)) },
    { name: 'Unisex', value: parseFloat(p.gender_unisex?.toFixed(1)) },
  ]
  const skinData = [
    { name: 'Dry', value: parseFloat(p.skin_dry_score?.toFixed(1)) },
    { name: 'Oily', value: parseFloat(p.skin_oily_score?.toFixed(1)) },
    { name: 'Combo', value: parseFloat(p.skin_combo_score?.toFixed(1)) },
  ]

  return (
    <div style={{ background: '#111827', borderRadius: '12px', padding: '1.5rem', border: '1px solid #1f2937' }}>
      <p style={{ color: '#9ca3af', fontSize: '0.8rem', fontWeight: 700, marginBottom: '0.5rem', textTransform: 'uppercase' }}>
        Gender Expression Fit
      </p>
      <ResponsiveContainer width="100%" height={140}>
        <RePieChart>
          <Pie data={genderData} cx="50%" cy="50%" outerRadius={55} dataKey="value" strokeWidth={0}>
            {genderData.map((_, i) => <Cell key={i} fill={GENDER_COLORS[i]} />)}
          </Pie>
          <Tooltip
            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#e5e7eb' }}
            formatter={v => [v?.toFixed(1), 'Score']}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ color: '#9ca3af', fontSize: '0.75rem' }} />
        </RePieChart>
      </ResponsiveContainer>

      <p style={{ color: '#9ca3af', fontSize: '0.8rem', fontWeight: 700, margin: '0.5rem 0', textTransform: 'uppercase' }}>
        Skin Type Distribution
      </p>
      <ResponsiveContainer width="100%" height={140}>
        <RePieChart>
          <Pie data={skinData} cx="50%" cy="50%" innerRadius={30} outerRadius={55} dataKey="value" strokeWidth={0}>
            {skinData.map((_, i) => <Cell key={i} fill={SKIN_COLORS[i]} />)}
          </Pie>
          <Tooltip
            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#e5e7eb' }}
            formatter={v => [v?.toFixed(1), 'Score']}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ color: '#9ca3af', fontSize: '0.75rem' }} />
        </RePieChart>
      </ResponsiveContainer>
    </div>
  )
}
