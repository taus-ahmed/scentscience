import React, { useState } from 'react'

export default function NLPConclusion({ conclusion, instagramBrief, perfumeName }) {
  const [copied, setCopied] = useState(null)

  const copyAll = async () => {
    await navigator.clipboard.writeText(instagramBrief || '')
    setCopied('all')
    setTimeout(() => setCopied(null), 2000)
  }

  const bullets = (instagramBrief || '').split('\n').filter(l => l.trim().startsWith('•'))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginBottom: '2rem' }}>
      {/* Expert Conclusion */}
      <div style={{
        background: 'linear-gradient(135deg, #1e1b4b 0%, #111827 100%)',
        borderRadius: '16px', padding: '2rem',
        border: '1px solid #312e81',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <span style={{ fontSize: '1.2rem' }}>⚗</span>
          <p style={{ color: '#a78bfa', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            ScentScience Analysis
          </p>
        </div>
        <p style={{ color: '#e5e7eb', lineHeight: 1.7, fontSize: '0.95rem' }}>
          {conclusion || 'Generating expert analysis…'}
        </p>
      </div>

      {/* Instagram Brief */}
      <div style={{
        background: '#111827', borderRadius: '16px', padding: '2rem',
        border: '1px solid #1f2937',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ fontSize: '1.2rem' }}>📱</span>
            <p style={{ color: '#9ca3af', fontSize: '0.8rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Instagram Brief — {perfumeName}
            </p>
          </div>
          <button
            onClick={copyAll}
            style={{
              padding: '0.4rem 1rem', background: copied === 'all' ? '#059669' : '#374151',
              border: 'none', borderRadius: '6px', color: '#e5e7eb',
              cursor: 'pointer', fontSize: '0.78rem', fontWeight: 600,
              transition: 'background 0.2s',
            }}
          >
            {copied === 'all' ? '✓ Copied!' : 'Copy All'}
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {bullets.length > 0 ? bullets.map((bullet, i) => (
            <BulletPoint key={i} text={bullet} index={i} />
          )) : (
            <p style={{ color: '#4b5563', fontSize: '0.9rem' }}>
              {instagramBrief || 'Generating talking points…'}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function BulletPoint({ text, index }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(text.replace(/^•\s*/, ''))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const colors = ['#a78bfa', '#34d399', '#60a5fa', '#fbbf24', '#f472b6']
  const color = colors[index % colors.length]

  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
      padding: '0.75rem 1rem', background: '#1f2937', borderRadius: '8px',
      borderLeft: `3px solid ${color}`,
    }}>
      <p style={{ color: '#e5e7eb', fontSize: '0.88rem', lineHeight: 1.5, flex: 1 }}>
        {text.replace(/^•\s*/, '')}
      </p>
      <button
        onClick={copy}
        style={{
          marginLeft: '1rem', padding: '0.2rem 0.6rem',
          background: copied ? '#059669' : '#374151',
          border: 'none', borderRadius: '4px', color: '#9ca3af',
          cursor: 'pointer', fontSize: '0.72rem', flexShrink: 0,
          transition: 'background 0.2s',
        }}
      >
        {copied ? '✓' : 'Copy'}
      </button>
    </div>
  )
}
