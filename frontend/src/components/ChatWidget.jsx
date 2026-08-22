import React, { useState, useRef, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { sendChat } from '../api/client.js'

const WELCOME = {
  id: 'welcome',
  role: 'bot',
  text: "Hi! I'm your fragrance guide. Ask me anything:\n• \"Best perfume for a job interview\"\n• \"What lasts all day in summer?\"\n• \"Compare Sauvage vs Bleu de Chanel\"\n• \"What's similar to Chanel No 5?\"",
  perfumes: [],
}

const s = {
  fab: {
    position: 'fixed', bottom: '1.5rem', right: '1rem', zIndex: 1000,
    width: '56px', height: '56px', borderRadius: '50%',
    background: 'linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)',
    border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center',
    justifyContent: 'center', boxShadow: '0 4px 20px rgba(124,58,237,0.5)',
    transition: 'transform 0.15s, box-shadow 0.15s',
    color: '#fff', fontSize: '1.4rem',
  },
  panel: {
    position: 'fixed', bottom: '5.5rem', right: '0.5rem', zIndex: 999,
    width: 'min(380px, calc(100vw - 1rem))',
    height: 'min(520px, calc(100dvh - 7rem))',
    borderRadius: '16px',
    background: 'linear-gradient(180deg, #0f0f1f 0%, #0a0a14 100%)',
    border: '1px solid #312e81', boxShadow: '0 8px 40px rgba(0,0,0,0.7)',
    display: 'flex', flexDirection: 'column', overflow: 'hidden',
  },
  header: {
    padding: '1rem 1.25rem',
    background: 'linear-gradient(135deg, #1e1b4b 0%, #1a1a3e 100%)',
    borderBottom: '1px solid #312e81',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
  },
  headerTitle: { color: '#a78bfa', fontWeight: 700, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.5rem' },
  closeBtn: {
    background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer',
    fontSize: '1.1rem', padding: '0.2rem', lineHeight: 1,
  },
  messages: {
    flex: 1, overflowY: 'auto', padding: '1rem',
    display: 'flex', flexDirection: 'column', gap: '0.75rem',
  },
  bubble: (role) => ({
    maxWidth: '88%',
    alignSelf: role === 'user' ? 'flex-end' : 'flex-start',
    background: role === 'user'
      ? 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)'
      : '#1e1b4b',
    border: role === 'user' ? 'none' : '1px solid #312e81',
    borderRadius: role === 'user' ? '14px 14px 4px 14px' : '14px 14px 14px 4px',
    padding: '0.6rem 0.9rem',
    color: '#e2e8f0',
    fontSize: '0.85rem',
    lineHeight: 1.5,
    whiteSpace: 'pre-wrap',
  }),
  thinking: {
    alignSelf: 'flex-start', color: '#6b7280', fontSize: '0.82rem',
    padding: '0.4rem 0.9rem', fontStyle: 'italic',
  },
  suggCard: {
    background: '#111827',
    border: '1px solid #374151',
    borderRadius: '8px',
    padding: '0.5rem 0.75rem',
    cursor: 'pointer',
    marginTop: '0.5rem',
    transition: 'border-color 0.15s, background 0.15s',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    gap: '0.5rem',
  },
  suggName: { color: '#c4b5fd', fontWeight: 600, fontSize: '0.82rem' },
  suggBrand: { color: '#6b7280', fontSize: '0.75rem' },
  suggAccords: { display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.25rem' },
  accordPill: {
    background: '#1e1b4b', color: '#a78bfa', borderRadius: '999px',
    padding: '0.1rem 0.4rem', fontSize: '0.68rem',
  },
  footer: {
    padding: '0.75rem 1rem',
    borderTop: '1px solid #1e1b4b',
    display: 'flex', gap: '0.5rem',
  },
  input: {
    flex: 1, background: '#1e1b4b', border: '1px solid #312e81',
    borderRadius: '8px', color: '#e2e8f0', padding: '0.5rem 0.75rem',
    fontSize: '0.85rem', outline: 'none', resize: 'none', fontFamily: 'inherit',
  },
  sendBtn: {
    background: 'linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%)',
    border: 'none', borderRadius: '8px', color: '#fff',
    padding: '0 0.9rem', cursor: 'pointer', fontSize: '1rem',
    flexShrink: 0,
  },
}

function renderText(text) {
  // Bold **X** and bullet • as styled spans
  return text.split('\n').map((line, i) => {
    const parts = line.split(/(\*\*[^*]+\*\*)/)
    return (
      <span key={i}>
        {parts.map((p, j) =>
          p.startsWith('**') && p.endsWith('**')
            ? <strong key={j} style={{ color: '#c4b5fd' }}>{p.slice(2, -2)}</strong>
            : <span key={j}>{p}</span>
        )}
        {i < text.split('\n').length - 1 && <br />}
      </span>
    )
  })
}

function PerfumeCard({ p, onClick }) {
  const [hover, setHover] = useState(false)
  return (
    <div
      style={{ ...s.suggCard, borderColor: hover ? '#7c3aed' : '#374151', background: hover ? '#1a1a2e' : '#111827' }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={() => onClick(p)}
    >
      <div style={{ minWidth: 0 }}>
        <div style={s.suggName}>{p.name}</div>
        <div style={s.suggBrand}>{p.brand} · {p.concentration}</div>
        {p.accords && p.accords.length > 0 && (
          <div style={s.suggAccords}>
            {p.accords.slice(0, 3).map(a => (
              <span key={a} style={s.accordPill}>{a}</span>
            ))}
          </div>
        )}
      </div>
      <span style={{ color: '#4f46e5', fontSize: '0.8rem', flexShrink: 0 }}>→</span>
    </div>
  )
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const navigate = useNavigate()
  const location = useLocation()

  // Presentation / screen-recording mode: hide the guide entirely.
  // Trigger with a URL param (?clean=1 or ?present=1). Once mounted you can also
  // toggle it live by pressing "g" (except while typing in a field).
  const cleanParam = new URLSearchParams(location.search).get('clean')
  const presentParam = new URLSearchParams(location.search).get('present')
  const forcedHidden = ['1', 'true', 'yes'].includes((cleanParam || presentParam || '').toLowerCase())
  const [hidden, setHidden] = useState(forcedHidden)

  useEffect(() => { setHidden(forcedHidden) }, [forcedHidden])

  useEffect(() => {
    const onKeyDown = (e) => {
      const tag = (e.target?.tagName || '').toLowerCase()
      const typing = tag === 'input' || tag === 'textarea' || e.target?.isContentEditable
      if (typing) return
      if (e.key === 'g' || e.key === 'G') setHidden(v => !v)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')

    const userMsg = { id: Date.now(), role: 'user', text, perfumes: [] }
    setMessages(prev => [...prev, userMsg])
    setLoading(true)

    try {
      const data = await sendChat(text)
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'bot',
        text: data.answer,
        perfumes: data.perfumes || [],
        action: data.action,
      }])
    } catch {
      setMessages(prev => [...prev, {
        id: Date.now() + 1,
        role: 'bot',
        text: 'Something went wrong. Please try again.',
        perfumes: [],
      }])
    } finally {
      setLoading(false)
    }
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const onPerfumeClick = (p) => {
    navigate(`/?name=${encodeURIComponent(p.name)}&brand=${encodeURIComponent(p.brand)}`)
    setOpen(false)
  }

  // Hidden for screen recording — render nothing (no FAB, no panel).
  if (hidden) return null

  return (
    <>
      {open && (
        <div style={s.panel}>
          <div style={s.header}>
            <div style={s.headerTitle}>
              <span>⬡</span>
              <span>DecodeScents Guide</span>
            </div>
            <button style={s.closeBtn} onClick={() => setOpen(false)} title="Close">✕</button>
          </div>

          <div style={s.messages}>
            {messages.map(msg => (
              <div key={msg.id} style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={s.bubble(msg.role)}>
                  {renderText(msg.text)}
                </div>
                {msg.perfumes && msg.perfumes.length > 0 && (
                  <div style={{ alignSelf: 'flex-start', width: '96%' }}>
                    {msg.perfumes.map(p => (
                      <PerfumeCard key={p.id} p={p} onClick={onPerfumeClick} />
                    ))}
                  </div>
                )}
              </div>
            ))}
            {loading && <div style={s.thinking}>Thinking…</div>}
            <div ref={bottomRef} />
          </div>

          <div style={s.footer}>
            <textarea
              ref={inputRef}
              style={s.input}
              rows={1}
              placeholder="Ask about any fragrance…"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKey}
            />
            <button style={s.sendBtn} onClick={send} disabled={loading}>↑</button>
          </div>
        </div>
      )}

      <button
        style={s.fab}
        onClick={() => setOpen(v => !v)}
        title={open ? 'Close chat' : 'Ask the fragrance guide'}
        onMouseEnter={e => {
          e.currentTarget.style.transform = 'scale(1.08)'
          e.currentTarget.style.boxShadow = '0 6px 28px rgba(124,58,237,0.7)'
        }}
        onMouseLeave={e => {
          e.currentTarget.style.transform = 'scale(1)'
          e.currentTarget.style.boxShadow = '0 4px 20px rgba(124,58,237,0.5)'
        }}
      >
        {open ? '✕' : '💬'}
      </button>
    </>
  )
}
