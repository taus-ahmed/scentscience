import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Search from './pages/Search.jsx'
import ChatWidget from './components/ChatWidget.jsx'

const NAV_BG = { background: 'linear-gradient(135deg, #0d0d1a 0%, #1a1a2e 100%)', borderBottom: '1px solid #2a2a4a' }
const LOGO_COLOR = { color: '#a78bfa', textDecoration: 'none' }
const LINK_COLOR = { color: '#94a3b8', textDecoration: 'none' }

export default function App() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <BrowserRouter>
      <nav style={NAV_BG} className="flex items-center justify-between px-4 py-3 sm:px-8">
        <Link to="/" style={LOGO_COLOR} className="text-lg font-black tracking-tight sm:text-xl">
          ⬡ ScentScience
        </Link>

        {/* Desktop links */}
        <div className="hidden sm:flex items-center gap-6">
          <Link to="/" style={LINK_COLOR} className="text-sm hover:opacity-80 transition-opacity">Dashboard</Link>
          <Link to="/search" style={LINK_COLOR} className="text-sm hover:opacity-80 transition-opacity">Browse</Link>
        </div>

        {/* Mobile hamburger */}
        <button
          className="sm:hidden p-1 rounded text-lg leading-none"
          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer' }}
          onClick={() => setMenuOpen(v => !v)}
          aria-label="Toggle navigation"
        >
          {menuOpen ? '✕' : '☰'}
        </button>
      </nav>

      {/* Mobile dropdown */}
      {menuOpen && (
        <div style={{ background: '#1a1a2e', borderBottom: '1px solid #2a2a4a' }}
          className="sm:hidden flex flex-col px-5 py-4 gap-4">
          <Link to="/" style={LINK_COLOR} className="text-sm" onClick={() => setMenuOpen(false)}>Dashboard</Link>
          <Link to="/search" style={LINK_COLOR} className="text-sm" onClick={() => setMenuOpen(false)}>Browse</Link>
        </div>
      )}

      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/search" element={<Search />} />
      </Routes>
      <ChatWidget />
    </BrowserRouter>
  )
}
