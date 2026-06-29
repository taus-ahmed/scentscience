import React from 'react'
import {
  AreaChart, Area,
  BarChart as ReBarChart, Bar,
  XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell,
} from 'recharts'

const TIP_STYLE = {
  background: '#1f2937', border: '1px solid #374151',
  borderRadius: '8px', color: '#e5e7eb',
}

function getDecayData(p) {
  const lng = p.longevity_hours || 6
  const candidates = [
    { t: 0, strength: p.sillage_score || 0 },
    { t: 1, strength: p.proj_1hr || 0 },
    { t: 3, strength: p.proj_3hr || 0 },
    { t: 6, strength: p.proj_6hr || 0 },
    { t: 8, strength: p.proj_8hr || 0 },
  ]
  const pts = candidates.filter(pt => pt.t < lng)
  pts.push({ t: Math.round(lng * 10) / 10, strength: 0 })
  return pts
}

export default function LongevityDecayChart({ predictions: p }) {
  const data = getDecayData(p)
  const ticks = data.map(d => d.t)

  return (
    <div className="rounded-xl p-4 sm:p-6" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9ca3af' }}>
        Performance over time
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 5, right: 10, bottom: 0, left: -20 }}>
          <defs>
            <linearGradient id="decayGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.35} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" />
          <XAxis
            dataKey="t"
            type="number"
            domain={[0, 'dataMax']}
            ticks={ticks}
            tickFormatter={v => `${v}h`}
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 10]}
            tick={{ fill: '#6b7280', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            contentStyle={TIP_STYLE}
            labelFormatter={v => `${v}h after application`}
            formatter={v => [v?.toFixed(1), 'Strength']}
          />
          <Area
            type="monotone"
            dataKey="strength"
            stroke="#6366f1"
            strokeWidth={2}
            fill="url(#decayGrad)"
            dot={false}
            activeDot={{ r: 4, fill: '#818cf8' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export function TimeOfDayChart({ predictions: p }) {
  const data = [
    { name: 'Morning',   value: p.time_morning,   color: '#fbbf24' },
    { name: 'Afternoon', value: p.time_afternoon,  color: '#fb923c' },
    { name: 'Evening',   value: p.time_evening,    color: '#a78bfa' },
    { name: 'Night',     value: p.time_night,      color: '#3b82f6' },
  ]

  return (
    <div className="rounded-xl p-4 sm:p-6" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-3 sm:mb-4" style={{ color: '#9ca3af' }}>
        Time of Day
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <ReBarChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1a2030" />
          <XAxis dataKey="name" tick={{ fill: '#d1d5db', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 10]} tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={TIP_STYLE}
            formatter={v => [v?.toFixed(1), 'Score']}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
          </Bar>
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  )
}
