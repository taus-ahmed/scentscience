import React from 'react'

export default function ScoreCard({ label, value, sub, color = '#a78bfa' }) {
  return (
    <div
      style={{ background: '#111827', border: `1px solid ${color}22`, borderRadius: '12px' }}
      className="p-3 sm:p-4 flex flex-col gap-1.5"
    >
      <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: '#6b7280' }}>
        {label}
      </span>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl sm:text-3xl font-black leading-none" style={{ color }}>
          {value}
        </span>
        <span className="text-xs" style={{ color: '#4b5563' }}>{sub}</span>
      </div>
    </div>
  )
}
