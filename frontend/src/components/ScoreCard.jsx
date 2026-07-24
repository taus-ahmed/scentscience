import React from 'react'

export default function ScoreCard({ label, value, sub, color = '#C9A84C' }) {
  return (
    <div
      style={{ background: '#111729', border: `1px solid ${color}22`, borderRadius: '12px' }}
      className="p-3 sm:p-4 flex flex-col gap-1.5 glass-card"
    >
      <span className="text-[0.65rem] sm:text-xs font-semibold uppercase tracking-wider leading-tight" style={{ color: '#5A5245' }}>
        {label}
      </span>
      <div className="flex items-baseline gap-1 min-w-0">
        <span className="text-lg sm:text-3xl font-black leading-none break-words" style={{ color }}>
          {value}
        </span>
        <span className="text-[0.65rem] sm:text-xs flex-shrink-0" style={{ color: '#4A4235' }}>{sub}</span>
      </div>
    </div>
  )
}
