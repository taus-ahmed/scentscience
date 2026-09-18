import React from 'react'

const FOOTER_BG = {
  background: 'linear-gradient(135deg, #080C15 0%, #0D1220 100%)',
  borderTop: '1px solid rgba(201,168,76,0.12)',
}
const HEADING_STYLE = {
  color: '#C9A84C',
  fontFamily: "'Playfair Display', Georgia, serif",
}
const BODY_STYLE = { color: '#9B8E7A' }
const LINK_STYLE = {
  color: '#C9A84C',
  textDecoration: 'none',
  borderBottom: '1px solid rgba(201,168,76,0.35)',
}

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer style={FOOTER_BG} className="mt-12 px-4 py-10 sm:px-8">
      <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 text-center">
        <h2 style={HEADING_STYLE} className="text-lg font-black tracking-tight sm:text-xl">
          About DecodeScents
        </h2>
        <p style={BODY_STYLE} className="text-sm leading-relaxed sm:text-base">
          DecodeScents is a machine learning platform predicting 35+ contextual
          performance outputs for colognes and perfumes.
        </p>

        <div className="mt-4 flex flex-col items-center gap-1 text-sm sm:text-base">
          <span style={BODY_STYLE}>
            Built by <span style={{ color: '#C9A84C', fontWeight: 600 }}>Mohammed Tauseef Ahmed</span>
          </span>
          <a href="mailto:decodescent9@gmail.com" style={LINK_STYLE}>
            decodescent9@gmail.com
          </a>
          <span style={BODY_STYLE} className="text-xs opacity-70">
            For business inquiries, reach out anytime.
          </span>
        </div>

        <p style={BODY_STYLE} className="mt-6 text-xs opacity-60">
          © {year} Mohammed Tauseef Ahmed. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
