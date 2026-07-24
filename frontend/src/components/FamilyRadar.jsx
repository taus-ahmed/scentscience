import React from 'react'

// Kept the filename/export name (FamilyRadar) so imports stay unchanged, but this
// now renders a clean sorted horizontal bar list instead of a 17-spoke radar —
// far more legible, especially on mobile / screen recordings.

const FAMILY_NAMES = [
  'citrus', 'woody', 'floral', 'oriental', 'fresh', 'gourmand',
  'chypre', 'fougere', 'aquatic', 'spicy', 'earthy', 'green',
  'powdery', 'smoky', 'resinous', 'musky', 'animalic',
]

const FAMILY_COLORS = {
  citrus: '#D4B86A', woody: '#8B6914', floral: '#C4859A',
  oriental: '#C9A84C', fresh: '#5DB89C', gourmand: '#D4956B',
  chypre: '#7B9E6B', fougere: '#5B9BB5', aquatic: '#6B9BC4',
  spicy: '#C4614A', earthy: '#6B8B4A', green: '#7DAF6B',
  powdery: '#C4A8B5', smoky: '#7A7065', resinous: '#A87D3C',
  musky: '#C9B5A0', animalic: '#6B4A1C',
}

const cap = s => s.charAt(0).toUpperCase() + s.slice(1)

export default function FamilyRadar({ familyFeatures }) {
  if (!familyFeatures || typeof familyFeatures !== 'object') return null

  // Only families with real weight, sorted strongest-first, capped at the top 8.
  const rows = FAMILY_NAMES
    .map(f => ({ family: f, value: Math.round((familyFeatures[f] || 0) * 100) }))
    .filter(r => r.value > 0)
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)

  if (!rows.length) return null

  const max = Math.max(...rows.map(r => r.value), 1)

  return (
    <div className="rounded-xl p-4 sm:p-6 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-4" style={{ color: '#9B8E7A' }}>
        Note Family DNA
      </p>
      <div className="flex flex-col gap-3">
        {rows.map(({ family, value }) => {
          const color = FAMILY_COLORS[family] || '#8B7355'
          return (
            <div key={family}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm" style={{ color: '#E8DCC8' }}>{cap(family)}</span>
                <span className="text-xs font-bold" style={{ color }}>{value}%</span>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: '#1A2035' }}>
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${(value / max) * 100}%`, background: color }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
