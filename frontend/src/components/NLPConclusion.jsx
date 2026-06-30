import React, { useState } from 'react'

function confidenceMeta(score) {
  if (score == null) return null
  if (score > 0.85) return { label: 'High confidence', color: '#5DB89C', bg: '#081A13' }
  if (score >= 0.60) return { label: 'Medium confidence', color: '#C9A84C', bg: '#1A140A' }
  return { label: 'Low confidence — limited data', color: '#C4614A', bg: '#1A0E0E' }
}

export default function NLPConclusion({ conclusion, instagramBrief, perfumeName, confidenceScore, modelVersion }) {
  const [copied, setCopied] = useState(null)
  const meta = confidenceMeta(confidenceScore)

  const copyAll = async () => {
    try {
      await navigator.clipboard.writeText(instagramBrief || '')
      setCopied('all')
      setTimeout(() => setCopied(null), 2000)
    } catch (_) {}
  }

  const bullets = (instagramBrief || '').split('\n').filter(l => l.trim().startsWith('•'))

  return (
    <div className="flex flex-col gap-4 sm:gap-5 mb-6 sm:mb-8">
      {/* Expert conclusion — quote-like block */}
      <div
        style={{
          background: '#0D1117',
          borderLeft: '3px solid #C9A84C',
          borderRadius: '0 10px 10px 0',
          padding: '1.25rem 1.5rem',
        }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-3">
          <p className="text-xs font-bold uppercase tracking-wider" style={{ color: '#C9A84C' }}>
            ScentScience Analysis
          </p>
          <div className="flex flex-wrap gap-2">
            {meta && (
              <span
                className="px-2.5 py-1 rounded-full text-xs font-bold"
                style={{ background: meta.bg, border: `1px solid ${meta.color}40`, color: meta.color }}
              >
                {meta.label} · {(confidenceScore * 100).toFixed(0)}%
              </span>
            )}
            {modelVersion && (
              <span
                className="px-2.5 py-1 rounded-full text-xs font-semibold"
                style={{ background: '#141A2E', border: '1px solid rgba(201,168,76,0.15)', color: '#5A5245' }}
              >
                v{modelVersion}
              </span>
            )}
          </div>
        </div>
        <p className="text-sm sm:text-base leading-relaxed" style={{ color: '#E8DCC8', fontStyle: 'italic' }}>
          {conclusion || 'Generating expert analysis…'}
        </p>
      </div>

      {/* Instagram Brief */}
      <div className="rounded-xl p-4 sm:p-6 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4">
          <p className="text-xs font-bold uppercase tracking-wider" style={{ color: '#9B8E7A' }}>
            Instagram Brief —{' '}
            <span className="normal-case font-semibold" style={{ color: '#E8DCC8' }}>{perfumeName}</span>
          </p>
          <button
            onClick={copyAll}
            className="self-start sm:self-auto px-3 py-1.5 rounded text-xs font-semibold transition-colors"
            style={{
              background: copied === 'all' ? '#3D8F73' : '#1A2035',
              border: 'none', color: '#E8DCC8', cursor: 'pointer',
            }}
          >
            {copied === 'all' ? '✓ Copied!' : 'Copy All'}
          </button>
        </div>

        <div className="flex flex-col gap-2 sm:gap-2.5">
          {bullets.length > 0 ? bullets.map((bullet, i) => (
            <BulletPoint key={i} text={bullet} index={i} />
          )) : (
            <p className="text-sm" style={{ color: '#4A4235' }}>
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
    try {
      await navigator.clipboard.writeText(text.replace(/^•\s*/, ''))
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (_) {}
  }

  const colors = ['#C9A84C', '#5DB89C', '#6B9BC4', '#D4956B', '#C47D9A']
  const color = colors[index % colors.length]

  return (
    <div
      className="flex items-start justify-between gap-2 sm:gap-3 px-3 py-2.5 rounded-lg"
      style={{ background: '#141A2E', borderLeft: `2px solid ${color}` }}
    >
      <p className="text-sm leading-relaxed flex-1" style={{ color: '#E8DCC8' }}>
        {text.replace(/^•\s*/, '')}
      </p>
      <button
        onClick={copy}
        className="flex-shrink-0 px-2 py-0.5 rounded text-xs transition-colors"
        style={{
          background: copied ? '#3D8F73' : '#1A2035',
          border: 'none', color: '#9B8E7A', cursor: 'pointer',
        }}
      >
        {copied ? '✓' : 'Copy'}
      </button>
    </div>
  )
}
