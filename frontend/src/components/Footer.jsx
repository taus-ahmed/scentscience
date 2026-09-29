import React from 'react'

export default function Footer() {
  return (
    <footer
      className="w-full text-center py-4 text-xs"
      style={{ color: '#3A3428', borderTop: '1px solid rgba(201,168,76,0.06)', marginTop: '2rem' }}
    >
      © {new Date().getFullYear()} DecodeScents · Predictions are estimates based on community data
    </footer>
  )
}
