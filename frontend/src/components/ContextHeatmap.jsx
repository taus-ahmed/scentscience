import React from 'react'

const SEASONS = ['Spring', 'Summer', 'Fall', 'Winter']
const TIMES = ['Morning', 'Afternoon', 'Evening', 'Night']
const S_KEYS = ['season_spring', 'season_summer', 'season_fall', 'season_winter']
const T_KEYS = ['time_morning', 'time_afternoon', 'time_evening', 'time_night']

function getCellStyle(score) {
  if (score === null || score === undefined) return { background: 'rgba(30,35,55,0.6)' };
  const v = Math.max(0, Math.min(10, score));
  if (v <= 3) return { background: 'rgba(60,55,45,0.5)', color: '#9B8E7A' };
  if (v <= 5) return { background: 'rgba(110,90,50,0.65)', color: '#C4A86A' };
  if (v <= 7) return { background: 'rgba(160,128,58,0.8)', color: '#E8D4A0' };
  if (v <= 8.5) return { background: 'rgba(201,168,76,0.9)', color: '#fff' };
  return {
    background: 'rgba(220,185,90,1)',
    color: '#fff',
    boxShadow: '0 0 12px rgba(201,168,76,0.6)',
  };
}

export default function ContextHeatmap({ predictions: p }) {
  // Normalize each axis to 0-1 independently so mixed scales (e.g. season 0-10,
  // time 0-1) don't cause one dimension to dominate after multiplication.
  const sMax = Math.max(...S_KEYS.map(k => p[k] || 0), 0.001)
  const tMax = Math.max(...T_KEYS.map(k => p[k] || 0), 0.001)
  const raw = SEASONS.map((_, si) =>
    TIMES.map((_, ti) => {
      const s = (p[S_KEYS[si]] || 0) / sMax
      const t = (p[T_KEYS[ti]] || 0) / tMax
      return s * 0.7 + t * 0.3
    })
  )

  const maxVal = Math.max(...raw.flat(), 1)
  const cells = raw.map(row => row.map(v => v / maxVal))

  return (
    <div className="rounded-xl p-4 sm:p-6 glass-card" style={{ background: '#111729', border: '1px solid rgba(201,168,76,0.15)' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-1" style={{ color: '#9B8E7A' }}>
        Wear Intensity
      </p>
      <p className="text-xs mb-3" style={{ color: '#5A5245' }}>
        Higher = stronger projection &amp; season fit. Longevity increases in cooler weather independently.
      </p>
      <div className="overflow-x-auto">
        <div style={{ display: 'grid', gridTemplateColumns: '60px repeat(4, 1fr)', gap: '5px', minWidth: '260px' }}>
          {/* Header */}
          <div />
          {TIMES.map(t => (
            <div key={t} className="text-center pb-1" style={{ color: '#5A5245', fontSize: '0.68rem', lineHeight: 1.2 }}>
              {t}
            </div>
          ))}

          {/* Rows */}
          {SEASONS.map((season, si) => (
            <React.Fragment key={season}>
              <div className="flex items-center" style={{ color: '#5A5245', fontSize: '0.72rem' }}>
                {season}
              </div>
              {TIMES.map((_, ti) => {
                const norm = cells[si][ti]
                const score = norm * 10
                const cs = getCellStyle(score)
                return (
                  <div
                    key={ti}
                    title={`${season} ${TIMES[ti]}: ${score.toFixed(1)}`}
                    style={{
                      ...cs,
                      borderRadius: '6px',
                      padding: '10px 4px',
                      textAlign: 'center',
                    }}
                  >
                    <span style={{ fontSize: '0.68rem', fontWeight: 500, color: cs.color }}>
                      {score.toFixed(1)}
                    </span>
                  </div>
                )
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
      <p className="mt-3 text-xs" style={{ color: '#2A2520' }}>
        Intrinsic season × time fit — unaffected by your context selections
      </p>
    </div>
  )
}
