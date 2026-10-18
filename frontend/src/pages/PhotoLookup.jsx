/**
 * Phase 2 — Photo Lookup
 * User takes / uploads a bottle photo → Gemini reads label →
 * confirmation form (editable) → full prediction result.
 */
import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { identifyFromPhoto, predictFromPhoto } from '../api/client'

const CONCENTRATIONS = ['EDP', 'EDT', 'Extrait', 'Parfum', 'EDC', 'Unknown']

const SOURCE_LABEL = {
  database: { text: 'Found in database', color: '#059669' },
  inferred: { text: 'Estimated from AI knowledge — results may be less accurate', color: '#d97706' },
  not_found: { text: 'Not found', color: '#dc2626' },
}

export default function PhotoLookup() {
  const navigate = useNavigate()
  const fileRef = useRef(null)

  // Stage: 'idle' | 'identifying' | 'confirm' | 'predicting' | 'result' | 'error'
  const [stage, setStage] = useState('idle')
  const [preview, setPreview] = useState(null)
  const [identified, setIdentified] = useState({ brand: '', name: '', concentration: 'Unknown' })
  const [edited, setEdited]         = useState({ brand: '', name: '', concentration: 'Unknown' })
  const [result, setResult]         = useState(null)
  const [error, setError]           = useState(null)

  function handleFileChange(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setStage('identifying')
    setError(null)

    identifyFromPhoto(file)
      .then(data => {
        const id = {
          brand:         data.brand         || '',
          name:          data.name          || '',
          concentration: data.concentration || 'Unknown',
        }
        setIdentified(id)
        setEdited({ ...id })
        // Always go to confirm — even if Gemini couldn't read the label,
        // the user can type the name manually.
        setStage('confirm')
      })
      .catch(err => {
        const detail = err.response?.data?.detail
        // If the API errored but returned a parseable detail, show it.
        // Otherwise fall back to the confirm stage with blank fields so the
        // user can manually enter the name rather than hitting a dead end.
        if (detail && typeof detail === 'string' && detail !== 'Internal Server Error') {
          setError(detail)
          setStage('error')
        } else {
          // Show confirm with blank fields + a note
          const blank = { brand: '', name: '', concentration: 'Unknown' }
          setIdentified(blank)
          setEdited(blank)
          setError("Couldn't read the label automatically — please type the name below.")
          setStage('confirm')
        }
      })
  }

  function handleConfirm() {
    if (!edited.brand || !edited.name) {
      setError('Please fill in Brand and Name before confirming.')
      return
    }
    setError(null)
    setStage('predicting')

    predictFromPhoto(edited.brand, edited.name, edited.concentration)
      .then(data => {
        setResult(data)
        setStage('result')
      })
      .catch(err => {
        setError(err.response?.data?.detail || 'Prediction failed. Try again.')
        setStage('error')
      })
  }

  function reset() {
    setStage('idle')
    setPreview(null)
    setResult(null)
    setError(null)
    if (fileRef.current) fileRef.current.value = ''
  }

  // ── render ────────────────────────────────────────────────────────────────
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', padding: '24px 16px' }}>
      <div style={{ maxWidth: 520, margin: '0 auto' }}>

        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 28 }}>
          <button onClick={() => navigate('/')} style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--text-muted)', fontSize: 22, padding: 0,
          }}>←</button>
          <div>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: 'var(--text)' }}>
              Photo Lookup
            </h1>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-muted)' }}>
              Take a photo of the bottle to identify it
            </p>
          </div>
        </div>

        {/* Camera / Upload area */}
        {stage === 'idle' && (
          <div
            onClick={() => fileRef.current?.click()}
            style={{
              border: '2px dashed var(--border)',
              borderRadius: 16,
              padding: '48px 24px',
              textAlign: 'center',
              cursor: 'pointer',
              background: 'var(--surface)',
              transition: 'border-color .2s',
            }}
            onMouseOver={e => e.currentTarget.style.borderColor = 'var(--accent)'}
            onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <div style={{ fontSize: 52, marginBottom: 12 }}>📷</div>
            <p style={{ margin: 0, fontWeight: 600, color: 'var(--text)' }}>
              Tap to take a photo or upload
            </p>
            <p style={{ margin: '6px 0 0', fontSize: 13, color: 'var(--text-muted)' }}>
              Point the camera at the bottle label for best results
            </p>
          </div>
        )}

        {/* Hidden file input — capture=environment for mobile camera */}
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        {/* Photo preview */}
        {preview && stage !== 'idle' && (
          <div style={{ marginBottom: 20, borderRadius: 12, overflow: 'hidden',
                        boxShadow: '0 2px 12px rgba(0,0,0,.1)' }}>
            <img src={preview} alt="Bottle"
                 style={{ width: '100%', maxHeight: 260, objectFit: 'contain',
                          background: '#111' }} />
          </div>
        )}

        {/* Identifying spinner */}
        {stage === 'identifying' && (
          <Card>
            <Spinner />
            <p style={{ margin: '12px 0 0', textAlign: 'center', color: 'var(--text-muted)' }}>
              Reading the label…
            </p>
          </Card>
        )}

        {/* Confirmation form */}
        {stage === 'confirm' && (
          <Card>
            <h3 style={{ margin: '0 0 4px', fontSize: 16, color: 'var(--text)' }}>
              Is this correct?
            </h3>
            <p style={{ margin: '0 0 18px', fontSize: 13, color: 'var(--text-muted)' }}>
              Edit any field if the reading is wrong, then confirm.
            </p>

            <Field label="Brand">
              <input
                value={edited.brand}
                onChange={e => setEdited(p => ({ ...p, brand: e.target.value }))}
                placeholder="e.g. Dior"
                style={inputStyle}
              />
            </Field>

            <Field label="Fragrance Name">
              <input
                value={edited.name}
                onChange={e => setEdited(p => ({ ...p, name: e.target.value }))}
                placeholder="e.g. Sauvage"
                style={inputStyle}
              />
            </Field>

            <Field label="Concentration">
              <select
                value={edited.concentration}
                onChange={e => setEdited(p => ({ ...p, concentration: e.target.value }))}
                style={{ ...inputStyle, appearance: 'auto' }}
              >
                {CONCENTRATIONS.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </Field>

            {error && <p style={{ color: '#dc2626', fontSize: 13, margin: '4px 0 12px' }}>{error}</p>}

            <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
              <button onClick={reset} style={secondaryBtn}>Try again</button>
              <button onClick={handleConfirm} style={primaryBtn}>
                Confirm &amp; Predict
              </button>
            </div>
          </Card>
        )}

        {/* Predicting spinner */}
        {stage === 'predicting' && (
          <Card>
            <Spinner />
            <p style={{ margin: '12px 0 0', textAlign: 'center', color: 'var(--text-muted)' }}>
              Running prediction for <strong>{edited.name}</strong> by {edited.brand}…
            </p>
          </Card>
        )}

        {/* Result */}
        {stage === 'result' && result && (
          <>
            {/* Source badge */}
            {result.source && SOURCE_LABEL[result.source] && (
              <div style={{
                padding: '8px 14px', borderRadius: 8, marginBottom: 16,
                background: SOURCE_LABEL[result.source].color + '18',
                borderLeft: `3px solid ${SOURCE_LABEL[result.source].color}`,
                fontSize: 13, color: SOURCE_LABEL[result.source].color,
              }}>
                {SOURCE_LABEL[result.source].text}
              </div>
            )}

            {/* Message (inferred / not_found) */}
            {result.message && (
              <div style={{ background: 'var(--surface)', borderRadius: 10, padding: '12px 16px',
                            marginBottom: 16, fontSize: 13, color: 'var(--text-muted)' }}>
                {result.message}
              </div>
            )}

            {/* Not found — no prediction */}
            {result.source === 'not_found' && (
              <Card>
                <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                  Try searching by name on the Dashboard instead.
                </p>
                <button onClick={() => navigate('/')} style={{ ...primaryBtn, marginTop: 12 }}>
                  Go to Dashboard
                </button>
              </Card>
            )}

            {/* Prediction card */}
            {result.predictions && (
              <Card>
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)' }}>
                    {result.perfume?.name}
                  </div>
                  <div style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 2 }}>
                    {result.perfume?.brand}
                    {result.perfume?.concentration && result.perfume.concentration !== 'Unknown'
                      ? ` · ${result.perfume.concentration}` : ''}
                  </div>
                </div>

                <ScoreRow label="Longevity"
                  value={result.predictions.longevity_hours != null
                    ? `${result.predictions.longevity_hours.toFixed(1)}h` : '—'} />
                <ScoreRow label="Sillage"
                  value={result.predictions.sillage_score != null
                    ? `${result.predictions.sillage_score.toFixed(1)}/10` : '—'} />
                <ScoreRow label="Blind Buy"
                  value={result.predictions.blind_buy_score != null
                    ? `${result.predictions.blind_buy_score.toFixed(1)}/10` : '—'} />
                <ScoreRow label="Versatility"
                  value={result.predictions.versatility_score != null
                    ? `${result.predictions.versatility_score.toFixed(1)}/10` : '—'} />

                {/* Inferred notes */}
                {result.inferred_notes && (
                  <div style={{ marginTop: 16, paddingTop: 16,
                                borderTop: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 600 }}>
                      NOTES (AI INFERRED)
                    </div>
                    {['top_notes', 'middle_notes', 'base_notes'].map(tier => (
                      result.inferred_notes[tier]?.length > 0 && (
                        <div key={tier} style={{ marginBottom: 6 }}>
                          <span style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                            {tier.replace('_notes', '')}:{' '}
                          </span>
                          <span style={{ fontSize: 13 }}>
                            {result.inferred_notes[tier].join(', ')}
                          </span>
                        </div>
                      )
                    ))}
                  </div>
                )}

                <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
                  <button onClick={reset} style={secondaryBtn}>
                    Scan another
                  </button>
                  {result.db_match?.id && (
                    <button
                      onClick={() => navigate(`/?id=${result.db_match.id}&name=${encodeURIComponent(result.db_match.name)}&brand=${encodeURIComponent(result.db_match.brand)}`)}
                      style={primaryBtn}
                    >
                      Full report →
                    </button>
                  )}
                </div>
              </Card>
            )}
          </>
        )}

        {/* Error state */}
        {stage === 'error' && (
          <Card>
            <p style={{ color: '#dc2626', marginBottom: 16 }}>{error}</p>
            <button onClick={reset} style={primaryBtn}>Try again</button>
          </Card>
        )}

      </div>
    </div>
  )
}

// ── Small helpers ─────────────────────────────────────────────────────────────

function Card({ children }) {
  return (
    <div style={{
      background: 'var(--surface)', borderRadius: 14,
      padding: '20px 18px', boxShadow: '0 1px 6px rgba(0,0,0,.07)',
      marginBottom: 16,
    }}>
      {children}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={{ display: 'block', fontSize: 12, fontWeight: 600,
                      color: 'var(--text-muted)', marginBottom: 5,
                      textTransform: 'uppercase', letterSpacing: '.04em' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function ScoreRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between',
                  padding: '8px 0', borderBottom: '1px solid var(--border)',
                  fontSize: 14 }}>
      <span style={{ color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontWeight: 600, color: 'var(--text)' }}>{value}</span>
    </div>
  )
}

function Spinner() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center' }}>
      <div style={{
        width: 32, height: 32, borderRadius: '50%',
        border: '3px solid var(--border)',
        borderTopColor: 'var(--accent)',
        animation: 'spin .8s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '10px 12px', borderRadius: 8, fontSize: 15,
  border: '1.5px solid var(--border)', background: 'var(--bg)',
  color: 'var(--text)', boxSizing: 'border-box', outline: 'none',
}

const primaryBtn = {
  flex: 1, padding: '11px 0', borderRadius: 8, border: 'none',
  background: 'var(--accent)', color: '#fff', fontWeight: 600,
  fontSize: 15, cursor: 'pointer',
}

const secondaryBtn = {
  flex: 1, padding: '11px 0', borderRadius: 8,
  border: '1.5px solid var(--border)', background: 'transparent',
  color: 'var(--text)', fontWeight: 600, fontSize: 15, cursor: 'pointer',
}
