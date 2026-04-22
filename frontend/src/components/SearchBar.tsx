import { useRef } from 'react'

interface Props {
  onSubmit: (question: string) => void
  loading: boolean
  autoFocus?: boolean
  defaultValue?: string
}

const EXAMPLES = [
  'Top 5 stocks by most recent closing price?',
  'Highest revenue sector in 2024?',
  'Apple dividend history',
  'Companies with profit margin above 30%?',
  'Average Tesla volume in 2023?',
]

export function SearchBar({ onSubmit, loading, autoFocus, defaultValue }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = (inputRef.current?.value ?? '').trim()
    if (q && !loading && q.length <= 500) onSubmit(q)
  }

  function handleExample(ex: string) {
    if (inputRef.current) inputRef.current.value = ex
    if (!loading) onSubmit(ex)
  }

  return (
    <div style={{ width: '100%' }}>
      <form onSubmit={handleSubmit}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          background: 'rgba(255,255,255,0.05)',
          border: '0.5px solid rgba(255,255,255,0.1)',
          borderRadius: '10px',
          padding: '4px 4px 4px 14px',
        }}>
          <input
            ref={inputRef}
            type="text"
            defaultValue={defaultValue}
            placeholder="Ask anything about S&P 500 data…"
            disabled={loading}
            autoFocus={autoFocus}
            autoComplete="off"
            maxLength={500}
            style={{
              flex: 1,
              background: 'transparent',
              border: 'none',
              outline: 'none',
              fontSize: '14px',
              color: 'rgba(255,255,255,0.85)',
              padding: '9px 0',
              minWidth: 0,
            }}
          />
          <button
            type="submit"
            disabled={loading}
            style={{
              flexShrink: 0,
              background: loading ? 'rgba(255,255,255,0.12)' : '#ffffff',
              color: '#0a0a0a',
              border: 'none',
              borderRadius: '7px',
              padding: '8px 18px',
              fontSize: '13px',
              fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.5 : 1,
              transition: 'opacity 0.15s',
              whiteSpace: 'nowrap',
            }}
          >
            {loading ? 'Running…' : 'Ask'}
          </button>
        </div>
      </form>

      {/* Example chips */}
      <div style={{ marginTop: '10px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => handleExample(ex)}
            disabled={loading}
            style={{
              fontSize: '11px',
              padding: '5px 12px',
              borderRadius: '999px',
              border: '0.5px solid rgba(255,255,255,0.1)',
              background: 'transparent',
              color: 'rgba(255,255,255,0.38)',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.4 : 1,
              transition: 'color 0.12s, border-color 0.12s',
            }}
            onMouseEnter={e => {
              if (loading) return
              const el = e.currentTarget
              el.style.color = 'rgba(255,255,255,0.65)'
              el.style.borderColor = 'rgba(255,255,255,0.22)'
            }}
            onMouseLeave={e => {
              const el = e.currentTarget
              el.style.color = 'rgba(255,255,255,0.38)'
              el.style.borderColor = 'rgba(255,255,255,0.1)'
            }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}
