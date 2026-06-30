import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

const ADMIN_KEY = import.meta.env.VITE_ADMIN_KEY || 'SCENT_ADMIN_2025'

export default function AdminUnlock() {
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState(null) // null | 'activated' | 'invalid' | 'already'

  useEffect(() => {
    const key = searchParams.get('key')
    if (key === null) return
    if (key === ADMIN_KEY) {
      const already = localStorage.getItem('ss_admin_mode') === 'true'
      localStorage.setItem('ss_admin_mode', 'true')
      setStatus(already ? 'already' : 'activated')
    } else {
      setStatus('invalid')
    }
  }, [searchParams])

  const deactivate = () => {
    localStorage.removeItem('ss_admin_mode')
    setStatus('deactivated')
  }

  const isActive = localStorage.getItem('ss_admin_mode') === 'true'

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'transparent' }}
    >
      <div
        className="max-w-sm w-full rounded-2xl p-8 text-center"
        style={{
          background: '#111729',
          border: '1px solid rgba(201,168,76,0.2)',
        }}
      >
        <div
          className="text-3xl mb-4"
          style={{ color: '#C9A84C', fontFamily: "'Playfair Display', Georgia, serif" }}
        >
          ⬡
        </div>

        {status === 'activated' && (
          <>
            <p className="text-sm font-bold mb-2" style={{ color: '#5DB89C' }}>
              Admin mode activated
            </p>
            <p className="text-xs" style={{ color: '#4A4235' }}>
              AI note inference is now enabled for unknown fragrances.
            </p>
          </>
        )}

        {status === 'already' && (
          <p className="text-sm font-bold mb-2" style={{ color: '#C9A84C' }}>
            Admin mode is already active
          </p>
        )}

        {status === 'invalid' && (
          <p className="text-sm font-bold mb-2" style={{ color: '#C4614A' }}>
            Invalid key
          </p>
        )}

        {status === 'deactivated' && (
          <p className="text-sm font-bold mb-2" style={{ color: '#9B8E7A' }}>
            Admin mode deactivated
          </p>
        )}

        {status === null && (
          <p className="text-sm" style={{ color: '#4A4235' }}>
            {isActive ? 'Admin mode is currently active.' : 'No key provided.'}
          </p>
        )}

        {isActive && status !== 'deactivated' && (
          <button
            onClick={deactivate}
            className="mt-5 text-xs px-4 py-2 rounded-lg"
            style={{
              background: 'rgba(196,97,74,0.1)',
              border: '1px solid rgba(196,97,74,0.3)',
              color: '#C4614A',
              cursor: 'pointer',
            }}
          >
            Deactivate admin mode
          </button>
        )}
      </div>
    </div>
  )
}
