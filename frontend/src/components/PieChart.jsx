import React from 'react'
import { PieChart as RePieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const GENDER_COLORS = ['#6B9BC4', '#C47D9A', '#5DB89C']
const SKIN_COLORS = ['#C9A84C', '#D4956B', '#5DB89C']

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

  const tipStyle = {
    background: '#141A2E', border: '1px solid rgba(201,168,76,0.2)',
    borderRadius: '8px', color: '#E8DCC8',
  }

  return (
    <div className="rounded-xl p-4 sm:p-6 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: '#9B8E7A' }}>
        Gender Expression Fit
      </p>
      <ResponsiveContainer width="100%" height={140}>
        <RePieChart>
          <Pie data={genderData} cx="50%" cy="50%" outerRadius={55} dataKey="value" strokeWidth={0}>
            {genderData.map((_, i) => <Cell key={i} fill={GENDER_COLORS[i]} />)}
          </Pie>
          <Tooltip contentStyle={tipStyle} formatter={v => [v?.toFixed(1), 'Score']} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ color: '#9B8E7A', fontSize: '0.75rem' }} />
        </RePieChart>
      </ResponsiveContainer>

      <p className="text-xs font-bold uppercase tracking-wide mt-2 mb-2" style={{ color: '#9B8E7A' }}>
        Skin Type Distribution
      </p>
      <ResponsiveContainer width="100%" height={140}>
        <RePieChart>
          <Pie data={skinData} cx="50%" cy="50%" innerRadius={30} outerRadius={55} dataKey="value" strokeWidth={0}>
            {skinData.map((_, i) => <Cell key={i} fill={SKIN_COLORS[i]} />)}
          </Pie>
          <Tooltip contentStyle={tipStyle} formatter={v => [v?.toFixed(1), 'Score']} />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ color: '#9B8E7A', fontSize: '0.75rem' }} />
        </RePieChart>
      </ResponsiveContainer>
    </div>
  )
}
