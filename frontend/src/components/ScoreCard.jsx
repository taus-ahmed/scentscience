import React from 'react'

export default function ScoreCard({ label, value, sub, color = '#a78bfa' }) {
  return (
    <div style={{
      background: '#111827', border: `1px solid ${color}22`,
      borderRadius: '12px', padding: '1.25rem',
      display: 'flex', flexDirection: 'column', gap: '0.4rem',
    }}>
      <span style={{ color: '#6b7280', fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
        {label}
      </span>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.25rem' }}>
        <span style={{ fontSize: '2.2rem', fontWeight: 900, color, lineHeight: 1 }}>{value}</span>
        <span style={{ color: '#4b5563', fontSize: '0.8rem' }}>{sub}</span>
      </div>
    </div>
  )
}
