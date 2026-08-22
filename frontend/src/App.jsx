import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Search from './pages/Search.jsx'
import AdminUnlock from './pages/AdminUnlock.jsx'
import ChatWidget from './components/ChatWidget.jsx'

// Deterministic particle configs — no Math.random so values are stable across renders
const PARTICLE_DATA = Array.from({ length: 14 }, (_, i) => ({
  id: i,
  left: `${((i * 7 + 3) % 97) + 1}%`,
  size: i % 3 === 0 ? '3px' : '2px',
  dur: `${11 + (i % 5) * 1.8}s`,
  delay: `${-(i * 0.9)}s`,
  drift: `${((i % 7) - 3) * 22}px`,
  opacity: i % 4 === 0 ? 0.45 : 0.28,
}))

function Particles() {
  return (
    <>
      {PARTICLE_DATA.map(p => (
        <div
          key={p.id}
          className="particle"
          style={{
            left: p.left,
            width: p.size,
            height: p.size,
            background: `rgba(201,168,76,${p.opacity})`,
            '--p-drift': p.drift,
            '--p-dur': p.dur,
            animationDelay: p.delay,
          }}
        />
      ))}
    </>
  )
}

const NAV_BG = {
  background: 'linear-gradient(135deg, #080C15 0%, #0D1220 100%)',
  borderBottom: '1px solid rgba(201,168,76,0.12)',
}
const LOGO_COLOR = { color: '#C9A84C', textDecoration: 'none', fontFamily: "'Playfair Display', Georgia, serif" }
const LINK_COLOR = { color: '#9B8E7A', textDecoration: 'none' }

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <BrowserRouter>
      <nav style={NAV_BG} className="flex items-center justify-between px-4 py-3 sm:px-8">
        <Link to="/" style={LOGO_COLOR} className="text-lg font-black tracking-tight sm:text-xl">
          ⬡ DecodeScents
        </Link>

        {/* Desktop links */}
        <div className="hidden sm:flex items-center gap-6">
          <Link to="/" style={LINK_COLOR} className="text-sm hover:opacity-80 transition-opacity">Dashboard</Link>
          <Link to="/search" style={LINK_COLOR} className="text-sm hover:opacity-80 transition-opacity">Browse</Link>
        </div>

        {/* Mobile hamburger */}
        <button
          className="sm:hidden p-1 rounded text-lg leading-none"
          style={{ background: 'none', border: 'none', color: '#9B8E7A', cursor: 'pointer' }}
          onClick={() => setMenuOpen(v => !v)}
          aria-label="Toggle navigation"
        >
          {menuOpen ? '✕' : '☰'}
        </button>
      </nav>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div style={{ background: '#0D1220', borderBottom: '1px solid rgba(201,168,76,0.12)' }}
          className="sm:hidden flex flex-col px-5 py-4 gap-4">
          <Link to="/" style={LINK_COLOR} className="text-sm" onClick={() => setMenuOpen(false)}>Dashboard</Link>
          <Link to="/search" style={LINK_COLOR} className="text-sm" onClick={() => setMenuOpen(false)}>Browse</Link>
        </div>
      )}

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/search" element={<Search />} />
        <Route path="/admin-unlock" element={<AdminUnlock />} />
      </Routes>
      <ChatWidget />
      <Particles />
    </BrowserRouter>
  )
}
