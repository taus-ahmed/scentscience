import React, { useState } from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Search from './pages/Search.jsx'
import AdminUnlock from './pages/AdminUnlock.jsx'
import ChatWidget from './components/ChatWidget.jsx'

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
    </BrowserRouter>
  )
}
