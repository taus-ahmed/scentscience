import React from 'react'

function confidenceMeta(score) {
  if (score == null) return null
  if (score > 0.85) return { label: 'High', color: '#5DB89C', bg: '#081A13' }
  if (score >= 0.60) return { label: 'Medium', color: '#C9A84C', bg: '#1A140A' }
  return { label: 'Low', color: '#C4614A', bg: '#1A0E0E' }
}

// Compact scent-analysis block: a single tight paragraph + confidence badge.
// (Instagram Brief intentionally removed from the platform.)
export default function NLPConclusion({ conclusion, confidenceScore, modelVersion }) {
  const meta = confidenceMeta(confidenceScore)

  return (
    <div className="mb-6 sm:mb-8">
      <div
        style={{
          background: '#0D1117',
          borderLeft: '3px solid #C9A84C',
          borderRadius: '0 10px 10px 0',
          padding: '1rem 1.15rem',
        }}
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <p className="text-xs font-bold uppercase tracking-wider" style={{ color: '#C9A84C' }}>
            Scent Analysis
          </p>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {meta && (
              <span
                className="px-2 py-0.5 rounded-full text-xs font-bold whitespace-nowrap"
                style={{ background: meta.bg, border: `1px solid ${meta.color}40`, color: meta.color }}
              >
                {meta.label} · {(confidenceScore * 100).toFixed(0)}%
              </span>
            )}
            {modelVersion && (
              <span
                className="px-2 py-0.5 rounded-full text-xs font-semibold whitespace-nowrap"
                style={{ background: '#141A2E', border: '1px solid rgba(201,168,76,0.15)', color: '#5A5245' }}
              >
                v{modelVersion}
              </span>
            )}
          </div>
        </div>
        <p className="text-sm leading-relaxed" style={{ color: '#E8DCC8', fontStyle: 'italic' }}>
          {conclusion || 'Generating scent analysis…'}
        </p>
      </div>
    </div>
  )
}
