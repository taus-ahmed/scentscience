import React from 'react'
import {
  BarChart as ReBarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell
} from 'recharts'

export default function BarChart({ predictions: p }) {
  const data = [
    { name: 'Morning', value: p.time_morning, color: '#fbbf24' },
    { name: 'Afternoon', value: p.time_afternoon, color: '#fb923c' },
    { name: 'Evening', value: p.time_evening, color: '#a78bfa' },
    { name: 'Night', value: p.time_night, color: '#3b82f6' },
  ]

  const projData = [
    { name: '1h', value: p.proj_1hr },
    { name: '3h', value: p.proj_3hr },
    { name: '6h', value: p.proj_6hr },
    { name: '8h', value: p.proj_8hr },
  ]

  return (
    <div className="rounded-xl p-4 sm:p-6" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-2" style={{ color: '#9ca3af' }}>
        Time of Day Performance
      </p>
      <ResponsiveContainer width="100%" height={130}>
        <ReBarChart data={data} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 10]} tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#e5e7eb' }}
            formatter={v => [v?.toFixed(1), 'Score']}
          />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => <Cell key={i} fill={entry.color} />)}
          </Bar>
        </ReBarChart>
      </ResponsiveContainer>

      <p className="text-xs font-bold uppercase tracking-wide mt-4 mb-2" style={{ color: '#9ca3af' }}>
        Projection Arc
      </p>
      <ResponsiveContainer width="100%" height={110}>
        <ReBarChart data={projData} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis dataKey="name" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 10]} tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
          <Tooltip
            contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: '8px', color: '#e5e7eb' }}
            formatter={v => [v?.toFixed(1), 'Projection']}
          />
          <Bar dataKey="value" fill="#34d399" radius={[4, 4, 0, 0]} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  )
}
