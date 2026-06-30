import React, { useState } from 'react'

const PANEL_STYLE = {
  background: '#111729',
  border: '1px solid rgba(201,168,76,0.18)',
  borderRadius: '16px',
}

const INPUT_STYLE = {
  background: '#0D1117',
  border: '1px solid rgba(201,168,76,0.2)',
  borderRadius: '8px',
  color: '#E8DCC8',
  padding: '0.5rem 0.75rem',
  width: '100%',
  fontSize: '0.85rem',
  outline: 'none',
}

const SELECT_STYLE = {
  ...INPUT_STYLE,
  cursor: 'pointer',
}

const LABEL_STYLE = {
  display: 'block',
  fontSize: '0.7rem',
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  color: '#7A6E5F',
  marginBottom: '0.35rem',
}

const CARD_STYLE = {
  background: '#0D1117',
  border: '1px solid rgba(201,168,76,0.15)',
  borderRadius: '10px',
  padding: '0.75rem 1rem',
  cursor: 'pointer',
  textAlign: 'left',
  width: '100%',
  transition: 'border-color 0.15s',
}

const FAMILIES = [
  'floral', 'woody', 'oriental', 'fresh', 'citrus',
  'aquatic', 'fougere', 'chypre', 'gourmand', 'aromatic',
]

const CONCENTRATIONS = ['EDT', 'EDP', 'Parfum', 'EDC', 'Extrait']

export default function OutOfDBPanel({
  name,
  brand,
  similar = [],
  onSelectSimilar,
  onPredictFromNotes,
  loading = false,
}) {
  const [topNotes, setTopNotes] = useState('')
  const [middleNotes, setMiddleNotes] = useState('')
  const [baseNotes, setBaseNotes] = useState('')
  const [concentration, setConcentration] = useState('EDP')
  const [family, setFamily] = useState('')

  const parseNotes = (s) =>
    s.split(',').map((n) => n.trim()).filter(Boolean)

  const handleSubmit = (e) => {
    e.preventDefault()
    const top = parseNotes(topNotes)
    const middle = parseNotes(middleNotes)
    const base = parseNotes(baseNotes)
    if (!top.length && !middle.length && !base.length) return
    onPredictFromNotes({
      name: name || 'Custom Fragrance',
      brand: brand || 'Unknown',
      top_notes: top,
      middle_notes: middle,
      base_notes: base,
      concentration,
      family: family || undefined,
    })
  }

  const canSubmit =
    !loading && (topNotes.trim() || middleNotes.trim() || baseNotes.trim())

  return (
    <div style={PANEL_STYLE} className="max-w-5xl mx-auto mt-6 mb-16 px-4 sm:px-6 md:px-8 py-8 sm:py-10">

      {/* Header */}
      <div className="mb-8">
        <h2
          className="text-2xl sm:text-3xl font-bold mb-2"
          style={{ color: '#E8DCC8', fontFamily: "'Playfair Display', Georgia, serif" }}
        >
          We don&apos;t have this one yet
        </h2>
        <p className="text-sm" style={{ color: '#4A4235' }}>
          {name && (
            <span>
              <span style={{ color: '#C9A84C' }}>{brand ? `${brand} ` : ''}{name}</span>{' '}
              isn&apos;t in our database of 110,000+ fragrances.
            </span>
          )}
          {!name && "This fragrance isn't in our database yet."}
        </p>
      </div>

      {/* ── Similar fragrances ──────────────────────────────────────────────── */}
      {similar.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-1 h-px" style={{ background: 'rgba(201,168,76,0.12)' }} />
            <span
              className="text-xs font-bold uppercase tracking-widest"
              style={{ color: '#4A4235', fontFamily: "'Playfair Display', Georgia, serif" }}
            >
              Similar in our database
            </span>
            <div className="flex-1 h-px" style={{ background: 'rgba(201,168,76,0.12)' }} />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {similar.map((p) => (
              <button
                key={p.id}
                style={CARD_STYLE}
                onClick={() => onSelectSimilar(p.name, p.brand)}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(201,168,76,0.45)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = 'rgba(201,168,76,0.15)'
                }}
              >
                <p
                  className="text-xs font-semibold mb-0.5"
                  style={{ color: '#C9A84C' }}
                >
                  {p.brand}
                </p>
                <p
                  className="text-sm font-bold leading-tight"
                  style={{ color: '#E8DCC8', fontFamily: "'Playfair Display', Georgia, serif" }}
                >
                  {p.name}
                </p>
                {p.concentration && (
                  <p className="text-xs mt-0.5" style={{ color: '#5A5245' }}>
                    {p.concentration}
                  </p>
                )}
                <p
                  className="text-xs mt-2 font-medium"
                  style={{ color: '#5DB89C' }}
                >
                  Predict this instead →
                </p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Note entry form ──────────────────────────────────────────────────── */}
      <div>
        <div className="flex items-center gap-3 mb-4">
          <div className="flex-1 h-px" style={{ background: 'rgba(201,168,76,0.12)' }} />
          <span
            className="text-xs font-bold uppercase tracking-widest"
            style={{ color: '#4A4235', fontFamily: "'Playfair Display', Georgia, serif" }}
          >
            Know the notes? Get a prediction
          </span>
          <div className="flex-1 h-px" style={{ background: 'rgba(201,168,76,0.12)' }} />
        </div>

        <p className="text-xs mb-5" style={{ color: '#4A4235' }}>
          Enter the note pyramid (comma-separated) and we&apos;ll run our full ML models on it.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">

          {/* Notes row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label style={LABEL_STYLE}>Top notes</label>
              <input
                type="text"
                placeholder="Bergamot, Lemon, Neroli"
                value={topNotes}
                onChange={(e) => setTopNotes(e.target.value)}
                style={INPUT_STYLE}
              />
            </div>
            <div>
              <label style={LABEL_STYLE}>Heart / Middle notes</label>
              <input
                type="text"
                placeholder="Rose, Jasmine, Iris"
                value={middleNotes}
                onChange={(e) => setMiddleNotes(e.target.value)}
                style={INPUT_STYLE}
              />
            </div>
            <div>
              <label style={LABEL_STYLE}>Base notes</label>
              <input
                type="text"
                placeholder="Musk, Sandalwood, Vanilla"
                value={baseNotes}
                onChange={(e) => setBaseNotes(e.target.value)}
                style={INPUT_STYLE}
              />
            </div>
          </div>

          {/* Concentration + Family row */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label style={LABEL_STYLE}>Concentration</label>
              <select
                value={concentration}
                onChange={(e) => setConcentration(e.target.value)}
                style={SELECT_STYLE}
              >
                {CONCENTRATIONS.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={LABEL_STYLE}>Fragrance family (optional)</label>
              <select
                value={family}
                onChange={(e) => setFamily(e.target.value)}
                style={SELECT_STYLE}
              >
                <option value="">— select —</option>
                {FAMILIES.map((f) => (
                  <option key={f} value={f}>
                    {f.charAt(0).toUpperCase() + f.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full sm:w-auto px-8 py-2.5 rounded-xl text-sm font-bold"
            style={{
              background: canSubmit
                ? 'linear-gradient(135deg, #C9A84C, #A8873C)'
                : '#1A2035',
              color: canSubmit ? '#080C15' : '#3A3530',
              border: 'none',
              cursor: canSubmit ? 'pointer' : 'not-allowed',
              transition: 'opacity 0.15s',
            }}
          >
            {loading ? 'Predicting…' : 'Predict from notes'}
          </button>
        </form>
      </div>
    </div>
  )
}
