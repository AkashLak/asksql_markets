import { motion } from 'framer-motion'

const CAP_SENTINEL = '… results capped at'

function formatCell(val: string | number | null): string {
  if (val === null || val === '') return '—'
  if (typeof val === 'number') {
    if (Math.abs(val) >= 1e9)  return (val / 1e9).toLocaleString('en-US', { maximumFractionDigits: 2 }) + 'B'
    if (Math.abs(val) >= 1e6)  return (val / 1e6).toLocaleString('en-US', { maximumFractionDigits: 2 }) + 'M'
    if (Math.abs(val) >= 1000) return val.toLocaleString('en-US', { maximumFractionDigits: 2 })
    if (!Number.isInteger(val)) return Number(val.toPrecision(4)).toString()
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
      <div className="glass-card rounded-2xl px-5 py-10 text-center">
        <p className="text-sm text-slate-500 italic">No rows returned.</p>
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
    <div className="glass-card rounded-2xl overflow-x-auto results-table">
      {/* Header bar */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06] bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375m9.75-12.75c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125m19.5 0v1.5c0 .621-.504 1.125-1.125 1.125M2.25 5.625v1.5c0 .621.504 1.125 1.125 1.125m0 0h17.25m-17.25 0c0 .621.504 1.125 1.125 1.125" />
          </svg>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Results</span>
        </div>
        <span className="text-xs text-slate-600">
          {dataRows.length} row{dataRows.length !== 1 ? 's' : ''} · {columns.length} col{columns.length !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="w-full overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b border-white/[0.06]">
              {columns.map((col, ci) => (
                <th key={col}
                  className={`px-4 py-3 text-[11px] font-semibold text-slate-500 uppercase tracking-wider
                              whitespace-nowrap bg-white/[0.02] sticky top-0
                              ${isNumericCol[ci] ? 'text-right' : 'text-left'}`}
                >
                  {col.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, ri) => (
              <motion.tr
                key={ri}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: ri * 0.025, duration: 0.2 }}
                className="border-b border-white/[0.04] transition-colors"
              >
                {row.map((cell, ci) => (
                  <td key={ci}
                    className={`px-4 py-2.5 text-slate-300 whitespace-nowrap font-mono text-xs
                                ${isNumericCol[ci] ? 'text-right tabular-nums' : 'text-left'}`}
                  >
                    {formatCell(cell)}
                  </td>
                ))}
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>

      {capMsg && (
        <div className="px-5 py-2.5 bg-amber-950/30 border-t border-amber-900/40 flex items-center gap-2 text-xs text-amber-400">
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
          </svg>
          {capMsg} — add a tighter filter or LIMIT to refine results.
        </div>
      )}
    </div>
  )
}
