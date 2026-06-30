import React from 'react'
import {
  BarChart as ReBarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const TIP_STYLE = {
  background: '#141A2E', border: '1px solid rgba(201,168,76,0.2)',
  borderRadius: '8px', color: '#E8DCC8',
}
const TIP_FMT = v => [v?.toFixed(1), 'Score']

export default function SeasonBars({ predictions: p }) {
  const data = [
    { name: 'Spring', value: p.season_spring, color: '#5DB89C' },
    { name: 'Summer', value: p.season_summer, color: '#C9A84C' },
    { name: 'Fall',   value: p.season_fall,   color: '#D4956B' },
    { name: 'Winter', value: p.season_winter,  color: '#6B9BC4' },
  ]

  return (
    <div className="rounded-xl p-4 sm:p-6 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9B8E7A' }}>
        Season Fit
      </p>
      <ResponsiveContainer width="100%" height={190}>
        <ReBarChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1A2035" />
          <XAxis dataKey="name" tick={{ fill: '#E8DCC8', fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 10]} tick={{ fill: '#5A5245', fontSize: 10 }} axisLine={false} tickLine={false} />
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
    <div className="rounded-xl p-4 sm:p-6 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9B8E7A' }}>
        Best Occasions
      </p>
      <ResponsiveContainer width="100%" height={190}>
        <ReBarChart data={data} layout="vertical" margin={{ top: 0, right: 10, bottom: 0, left: 0 }}>
          <XAxis
            type="number"
            domain={[0, 10]}
            tick={{ fill: '#5A5245', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            tick={{ fill: '#E8DCC8', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={52}
          />
          <Tooltip contentStyle={TIP_STYLE} formatter={TIP_FMT} />
          <Bar dataKey="value" fill="#C9A84C" radius={[0, 4, 4, 0]} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  )
}
