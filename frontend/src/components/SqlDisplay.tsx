import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface Props { sql: string }

const KEYWORDS = new Set([
  'SELECT','FROM','WHERE','JOIN','LEFT','RIGHT','INNER','OUTER','CROSS','ON',
  'GROUP','ORDER','BY','HAVING','LIMIT','OFFSET','AND','OR','NOT','IN','EXISTS',
  'AS','DISTINCT','UNION','ALL','WITH','CASE','WHEN','THEN','ELSE','END',
  'BETWEEN','LIKE','ILIKE','IS','NULL','ASC','DESC','INSERT','UPDATE','DELETE',
  'CREATE','DROP','ALTER','TABLE','INTO','VALUES','SET','OVER','PARTITION',
  'WINDOW','FETCH','NEXT','ROWS','ONLY','TOP','RECURSIVE',
])

const FUNCTIONS = new Set([
  'COUNT','SUM','AVG','MAX','MIN','ROUND','COALESCE','NULLIF','DATE',
  'STRFTIME','ABS','CAST','LENGTH','TRIM','UPPER','LOWER','SUBSTR',
  'REPLACE','IIF','IFNULL','JULIANDAY','TYPEOF','PRINTF','INSTR',
  'DATETIME','TIME','YEAR','MONTH','DAY',
])

function highlightSQL(sql: string): React.ReactNode[] {
  const tokens = sql.split(/(\s+|[(),;*=<>!])/)
  return tokens.map((token, i) => {
    const upper = token.trim().toUpperCase()
    if (upper && KEYWORDS.has(upper)) {
      return <span key={i} style={{ color: '#7dd3fc' }}>{token}</span>
    }
    if (upper && FUNCTIONS.has(upper)) {
      return <span key={i} style={{ color: '#a5f3fc' }}>{token}</span>
    }
    return token
  })
}

export function SqlDisplay({ sql }: Props) {
  const [open, setOpen]     = useState(false)
  const [copied, setCopied] = useState(false)

  function copy(e: React.MouseEvent) {
    e.stopPropagation()
    navigator.clipboard.writeText(sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div style={{
      background: '#111111',
      border: '0.5px solid rgba(255,255,255,0.08)',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      {/* Header toggle */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '11px 16px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
        }}
      >
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          {open ? 'Hide SQL' : 'Show SQL'}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={copy}
            style={{
              fontSize: '11px',
              color: copied ? '#4ade80' : 'rgba(255,255,255,0.28)',
              background: 'transparent',
              border: '0.5px solid rgba(255,255,255,0.1)',
              borderRadius: '4px',
              padding: '3px 10px',
              cursor: 'pointer',
              transition: 'color 0.15s',
            }}
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
          <motion.span
            animate={{ rotate: open ? 180 : 0 }}
            transition={{ duration: 0.18 }}
            style={{ color: 'rgba(255,255,255,0.25)', display: 'flex' }}
          >
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
            </svg>
          </motion.span>
        </div>
      </button>

      {/* Collapsible SQL body */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22 }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ borderTop: '0.5px solid rgba(255,255,255,0.06)' }}>
              <pre style={{
                padding: '16px',
                fontSize: '12px',
                color: 'rgba(255,255,255,0.65)',
                background: 'transparent',
                overflowX: 'auto',
                lineHeight: 1.75,
                fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
              }}>
                {highlightSQL(sql)}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
