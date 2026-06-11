import React from 'react'
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard.jsx'
import Search from './pages/Search.jsx'

const styles = {
  nav: {
    display: 'flex', alignItems: 'center', gap: '2rem',
    padding: '1rem 2rem',
    background: 'linear-gradient(135deg, #0d0d1a 0%, #1a1a2e 100%)',
    borderBottom: '1px solid #2a2a4a',
  },
  logo: { fontSize: '1.4rem', fontWeight: 800, color: '#a78bfa', letterSpacing: '-0.5px', textDecoration: 'none' },
  link: { color: '#94a3b8', textDecoration: 'none', fontSize: '0.9rem' },
}

export default function App() {
  return (
    <BrowserRouter>
      <nav style={styles.nav}>
        <Link to="/" style={styles.logo}>⬡ ScentScience</Link>
        <Link to="/" style={styles.link}>Dashboard</Link>
        <Link to="/search" style={styles.link}>Browse</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/search" element={<Search />} />
      </Routes>
    </BrowserRouter>
  )
}
