import { motion } from 'framer-motion'

const CAP_SENTINEL = '… results capped at'

function formatCell(val: string | number | null): string {
  if (val === null || val === '') return '—'
  if (typeof val === 'number') {
    if (Math.abs(val) >= 1e9)  return (val / 1e9).toLocaleString('en-US', { maximumFractionDigits: 2 }) + 'B'
    if (Math.abs(val) >= 1e6)  return (val / 1e6).toLocaleString('en-US', { maximumFractionDigits: 2 }) + 'M'
    if (Math.abs(val) >= 1000) return val.toLocaleString('en-US', { maximumFractionDigits: 2 })
    if (!Number.isInteger(val)) return Number(val.toFixed(2)).toString()
    return val.toString()
  }
  return String(val)
}

interface Props {
  columns: string[]
  results: (string | number | null)[][]
}

export function ResultsTable({ columns, results }: Props) {
  if (results.length === 0) {
    return (
      <div style={{
        background: 'rgba(255,255,255,0.02)',
        border: '0.5px solid rgba(255,255,255,0.08)',
        borderRadius: '8px',
        padding: '40px 20px',
        textAlign: 'center',
      }}>
        <p style={{ fontSize: '13px', color: 'rgba(255,255,255,0.25)', fontStyle: 'italic' }}>No rows returned.</p>
      </div>
    )
  }

  const lastRow  = results[results.length - 1]
  const isCapped = typeof lastRow[0] === 'string' && lastRow[0].startsWith(CAP_SENTINEL)
  const dataRows = isCapped ? results.slice(0, -1) : results
  const capMsg   = isCapped ? String(lastRow[0]) : null

  const isNumericCol = columns.map((_, ci) =>
    dataRows.slice(0, 20).filter(r => r[ci] !== null && r[ci] !== '').every(r => typeof r[ci] === 'number')
  )

  return (
    <div className="results-table" style={{
      background: 'rgba(255,255,255,0.02)',
      border: '0.5px solid rgba(255,255,255,0.08)',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      {/* Row/col count */}
      <div style={{
        display: 'flex',
        justifyContent: 'flex-end',
        padding: '8px 16px',
        borderBottom: '0.5px solid rgba(255,255,255,0.06)',
      }}>
        <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.22)' }}>
          {dataRows.length} row{dataRows.length !== 1 ? 's' : ''} · {columns.length} col{columns.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div style={{ width: '100%', overflowX: 'auto' }}>
        <table style={{ width: '100%', fontSize: '13px', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '0.5px solid rgba(255,255,255,0.08)' }}>
              {columns.map((col, ci) => (
                <th key={col} style={{
                  padding: '9px 14px',
                  fontSize: '10px',
                  fontWeight: 500,
                  color: 'rgba(255,255,255,0.3)',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  whiteSpace: 'nowrap',
                  textAlign: isNumericCol[ci] ? 'right' : 'left',
                  background: 'rgba(255,255,255,0.02)',
                }}>
                  {col.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, ri) => (
              <motion.tr
                key={ri}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: ri * 0.018, duration: 0.18 }}
                style={{ borderBottom: '0.5px solid rgba(255,255,255,0.04)' }}
              >
                {row.map((cell, ci) => (
                  <td key={ci} style={{
                    padding: '8px 14px',
                    color: 'rgba(255,255,255,0.6)',
                    whiteSpace: 'nowrap',
                    fontFamily: 'ui-monospace, SFMono-Regular, monospace',
                    fontSize: '12px',
                    textAlign: isNumericCol[ci] ? 'right' : 'left',
                  }}>
                    {formatCell(cell)}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {capMsg && (
        <div style={{
          padding: '10px 16px',
          borderTop: '0.5px solid rgba(255,255,255,0.06)',
          fontSize: '11px',
          color: 'rgba(255,255,255,0.3)',
        }}>
          {capMsg} — add a tighter filter or LIMIT to refine results.
        </div>
      )}
    </div>
  )
}
