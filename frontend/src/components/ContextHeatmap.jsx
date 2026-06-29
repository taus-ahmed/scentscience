import React from 'react'

const SEASONS = ['Spring', 'Summer', 'Fall', 'Winter']
const TIMES = ['Morning', 'Afternoon', 'Evening', 'Night']
const S_KEYS = ['season_spring', 'season_summer', 'season_fall', 'season_winter']
const T_KEYS = ['time_morning', 'time_afternoon', 'time_evening', 'time_night']

export default function ContextHeatmap({ predictions: p }) {
  const raw = SEASONS.map((_, si) =>
    TIMES.map((_, ti) => (p[S_KEYS[si]] || 0) * (p[T_KEYS[ti]] || 0))
  )

  const maxVal = Math.max(...raw.flat(), 1)
  const cells = raw.map(row => row.map(v => v / maxVal))

  return (
    <div className="rounded-xl p-4 sm:p-6" style={{ background: '#111827', border: '1px solid #1f2937' }}>
      <p className="text-xs font-bold uppercase tracking-wide mb-4" style={{ color: '#9ca3af' }}>
        Best Moments
      </p>
      <div className="overflow-x-auto">
        <div style={{ display: 'grid', gridTemplateColumns: '60px repeat(4, 1fr)', gap: '5px', minWidth: '260px' }}>
          {/* Header */}
          <div />
          {TIMES.map(t => (
            <div key={t} className="text-center pb-1" style={{ color: '#6b7280', fontSize: '0.68rem', lineHeight: 1.2 }}>
              {t}
            </div>
          ))}

          {/* Rows */}
          {SEASONS.map((season, si) => (
            <React.Fragment key={season}>
              <div className="flex items-center" style={{ color: '#6b7280', fontSize: '0.72rem' }}>
                {season}
              </div>
              {TIMES.map((_, ti) => {
                const norm = cells[si][ti]
                const alpha = 0.06 + norm * 0.82
                return (
                  <div
                    key={ti}
                    title={`${season} ${TIMES[ti]}: ${(norm * 10).toFixed(1)}`}
                    style={{
                      background: `rgba(99, 102, 241, ${alpha})`,
                      borderRadius: '6px',
                      padding: '10px 4px',
                      textAlign: 'center',
                    }}
                  >
                    <span style={{ fontSize: '0.68rem', fontWeight: 500, color: norm > 0.55 ? '#e0e7ff' : '#4b5563' }}>
                      {(norm * 10).toFixed(1)}
                    </span>
                  </div>
                )
              })}
            </React.Fragment>
          ))}
        </div>
      </div>
      <p className="mt-3 text-xs" style={{ color: '#374151' }}>
        Intensity = season fit × time fit
      </p>
    </div>
  )
}
