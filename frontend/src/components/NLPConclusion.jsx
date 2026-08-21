import React from 'react'

function confidenceMeta(score) {
  if (score == null) return null
  if (score > 0.85) return { label: 'High', color: '#5DB89C', bg: '#081A13' }
  if (score >= 0.60) return { label: 'Medium', color: '#C9A84C', bg: '#1A140A' }
  return { label: 'Low', color: '#C4614A', bg: '#1A0E0E' }
}

// Confidence badge only — the "Scent Analysis" prose paragraph and Instagram
// Brief have been intentionally removed from the platform. Kept as its own
// component since NLPConclusion is also imported for the confidence badge
// placement next to the perfume title (see Dashboard.jsx identity card).
export default function NLPConclusion({ confidenceScore, modelVersion }) {
  const meta = confidenceMeta(confidenceScore)
  if (!meta && !modelVersion) return null

  return (
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
  )
}
