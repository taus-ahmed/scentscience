import React, { useState } from 'react'

function confidenceMeta(score) {
  if (score == null) return null
  if (score > 0.85) return { label: 'High confidence', color: '#34d399', bg: '#022c22' }
  if (score >= 0.60) return { label: 'Medium confidence', color: '#fbbf24', bg: '#1c1407' }
  return { label: 'Low confidence — limited data', color: '#ef4444', bg: '#1c0a0a' }
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
    <div className="flex flex-col gap-4 sm:gap-6 mb-6 sm:mb-8">
      {/* Expert Conclusion */}
      <div
        className="rounded-2xl p-4 sm:p-8"
        style={{ background: 'linear-gradient(135deg, #1e1b4b 0%, #111827 100%)', border: '1px solid #312e81' }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3 mb-3 sm:mb-4">
          <div className="flex items-center gap-2">
            <span className="text-lg sm:text-xl">⚗</span>
            <p className="text-xs font-bold uppercase tracking-wider" style={{ color: '#a78bfa' }}>
              ScentScience Analysis
            </p>
          </div>
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
                style={{ background: '#1f2937', border: '1px solid #374151', color: '#6b7280' }}
              >
                v{modelVersion}
              </span>
            )}
          </div>
        </div>
        <p className="text-sm sm:text-base leading-relaxed" style={{ color: '#e5e7eb' }}>
          {conclusion || 'Generating expert analysis…'}
        </p>
      </div>

      {/* Instagram Brief */}
      <div className="rounded-2xl p-4 sm:p-8" style={{ background: '#111827', border: '1px solid #1f2937' }}>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3 mb-4 sm:mb-5">
          <div className="flex items-center gap-2">
            <span className="text-lg sm:text-xl">📱</span>
            <p className="text-xs font-bold uppercase tracking-wider" style={{ color: '#9ca3af' }}>
              Instagram Brief — <span className="normal-case font-semibold" style={{ color: '#e5e7eb' }}>{perfumeName}</span>
            </p>
          </div>
          <button
            onClick={copyAll}
            className="self-start sm:self-auto px-4 py-1.5 rounded text-xs font-semibold transition-colors"
            style={{
              background: copied === 'all' ? '#059669' : '#374151',
              border: 'none', color: '#e5e7eb', cursor: 'pointer',
            }}
          >
            {copied === 'all' ? '✓ Copied!' : 'Copy All'}
          </button>
        </div>

        <div className="flex flex-col gap-2 sm:gap-3">
          {bullets.length > 0 ? bullets.map((bullet, i) => (
            <BulletPoint key={i} text={bullet} index={i} />
          )) : (
            <p className="text-sm" style={{ color: '#4b5563' }}>
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

  const colors = ['#a78bfa', '#34d399', '#60a5fa', '#fbbf24', '#f472b6']
  const color = colors[index % colors.length]

  return (
    <div
      className="flex items-start justify-between gap-2 sm:gap-3 px-3 py-2.5 sm:px-4 sm:py-3 rounded-lg"
      style={{ background: '#1f2937', borderLeft: `3px solid ${color}` }}
    >
      <p className="text-sm leading-relaxed flex-1" style={{ color: '#e5e7eb' }}>
        {text.replace(/^•\s*/, '')}
      </p>
      <button
        onClick={copy}
        className="flex-shrink-0 px-2 py-0.5 rounded text-xs transition-colors"
        style={{
          background: copied ? '#059669' : '#374151',
          border: 'none', color: '#9ca3af', cursor: 'pointer',
        }}
      >
        {copied ? '✓' : 'Copy'}
      </button>
    </div>
  )
}
