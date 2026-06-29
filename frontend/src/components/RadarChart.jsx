import React from 'react'
import {
  BarChart as ReBarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const TIP_STYLE = {
  background: '#1f2937', border: '1px solid #374151',
  borderRadius: '8px', color: '#e5e7eb',
}
const TIP_FMT = v => [v?.toFixed(1), 'Score']

export default function SeasonBars({ predictions: p }) {
  const data = [
    { name: 'Spring', value: p.season_spring, color: '#4ade80' },
    { name: 'Summer', value: p.season_summer, color: '#fbbf24' },
    { name: 'Fall',   value: p.season_fall,   color: '#fb923c' },
    { name: 'Winter', value: p.season_winter,  color: '#60a5fa' },
  ]

  return (
    <div className="rounded-xl p-4 sm:p-6" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9ca3af' }}>
        Season Fit
      </p>
      <ResponsiveContainer width="100%" height={190}>
        <ReBarChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" />
          <XAxis dataKey="name" tick={{ fill: '#d1d5db', fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 10]} tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={TIP_STYLE} formatter={TIP_FMT} />
          <Bar dataKey="value" radius={[6, 6, 0, 0]}>
            {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
          </Bar>
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function OccasionRanking({ predictions: p }) {
  const data = [
    { name: 'Office',   value: p.occ_office },
    { name: 'Date',     value: p.occ_date },
    { name: 'Casual',   value: p.occ_casual },
    { name: 'Formal',   value: p.occ_formal },
    { name: 'Sport',    value: p.occ_sport },
    { name: 'Travel',   value: p.occ_travel },
  ].sort((a, b) => (b.value || 0) - (a.value || 0))

  return (
    <div className="rounded-xl p-4 sm:p-6" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9ca3af' }}>
        Best Occasions
      </p>
      <ResponsiveContainer width="100%" height={190}>
        <ReBarChart data={data} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
          <XAxis
            type="number"
            domain={[0, 10]}
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: '#d1d5db', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
          />
          <Tooltip contentStyle={TIP_STYLE} formatter={TIP_FMT} />
          <Bar dataKey="value" fill="#a78bfa" radius={[0, 4, 4, 0]} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  )
}
