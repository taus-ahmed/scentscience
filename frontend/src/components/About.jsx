import React from 'react'

const PAGE_BG = { background: 'transparent', position: 'relative', zIndex: 1 }
const HERO_BG = { background: 'radial-gradient(ellipse at 50% 0%, rgba(201,168,76,0.05) 0%, transparent 65%)' }
const TITLE_STYLE = { color: '#E8DCC8', fontFamily: "'Playfair Display', Georgia, serif" }
const SUBTITLE_STYLE = { color: '#4A4235' }
const BODY_STYLE = { color: '#9B8E7A' }
const CARD_STYLE = {
  background: 'linear-gradient(135deg, #141A2E 0%, #111729 100%)',
  borderRadius: '16px',
  border: '1px solid rgba(201,168,76,0.2)',
}
const LINK_STYLE = {
  color: '#C9A84C',
  textDecoration: 'none',
  borderBottom: '1px solid rgba(201,168,76,0.35)',
}

export default function About() {
  const year = new Date().getFullYear()

  return (
    <div style={PAGE_BG} className="min-h-screen">
      {/* Hero — same treatment as the Dashboard */}
      <div className="px-4 pt-8 pb-6 text-center sm:px-8 sm:pt-12 sm:pb-8" style={HERO_BG}>
        <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-3 tracking-tight" style={TITLE_STYLE}>
          About DecodeScents
        </h1>
        <p className="text-sm sm:text-base" style={SUBTITLE_STYLE}>
          Who's behind it, and how to reach out.
        </p>
      </div>

      <div className="mx-auto max-w-2xl px-4 pb-16 sm:px-8">
        {/* Business enquiries, first */}
        <div style={CARD_STYLE} className="flex flex-col items-start gap-2 p-6">
          <span style={BODY_STYLE} className="text-sm sm:text-base">
            Built by <span style={{ color: '#C9A84C', fontWeight: 600 }}>Mohammed Tauseef Ahmed</span>
          </span>
          <a href="mailto:decodescent9@gmail.com" style={LINK_STYLE} className="text-sm sm:text-base">
            decodescent9@gmail.com
          </a>
          <span style={BODY_STYLE} className="text-xs opacity-60">
            © {year} Mohammed Tauseef Ahmed. All rights reserved.
          </span>
        </div>

        {/* About the application, second */}
        <p style={BODY_STYLE} className="mt-8 text-sm leading-relaxed sm:text-base">
          DecodeScents is a machine learning platform predicting 35+ contextual
          performance outputs for colognes and perfumes.
        </p>
      </div>
    </div>
  )
}
