const CAP_SENTINEL = '… results capped at'

function formatCell(val: string | number | null): string {
  if (val === null || val === '') return '—'
  if (typeof val === 'number') {
    // Large numbers: format with commas
    if (Math.abs(val) >= 1_000_000) return val.toLocaleString('en-US', { maximumFractionDigits: 2 })
    // Small decimals: cap at 4 places
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
      <p className="text-sm text-slate-400 italic py-4 text-center">
        No rows returned.
      </p>
    )
  }

  // Split off sentinel row if present
  const lastRow = results[results.length - 1]
  const isCapped = typeof lastRow[0] === 'string' && lastRow[0].startsWith(CAP_SENTINEL)
  const dataRows = isCapped ? results.slice(0, -1) : results
  const capMessage = isCapped ? String(lastRow[0]) : null

  return (
    <div className="rounded-lg border border-slate-700 overflow-hidden">
      <div className="px-4 py-2 bg-slate-800 border-b border-slate-700 flex items-center justify-between">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Results</span>
        <span className="text-xs text-slate-500">{dataRows.length} row{dataRows.length !== 1 ? 's' : ''}</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 bg-slate-800/50">
              {columns.map((col) => (
                <th
                  key={col}
                  className="px-4 py-2 text-left text-xs font-medium text-slate-400 uppercase tracking-wider whitespace-nowrap"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataRows.map((row, ri) => (
              <tr
                key={ri}
                className={`border-b border-slate-700/50 ${ri % 2 === 0 ? 'bg-slate-900' : 'bg-slate-800/30'} hover:bg-slate-700/30 transition-colors`}
              >
                {row.map((cell, ci) => (
                  <td key={ci} className="px-4 py-2 text-slate-300 whitespace-nowrap font-mono text-xs">
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {capMessage && (
        <div className="px-4 py-2 bg-amber-900/20 border-t border-amber-700/40 text-xs text-amber-400">
          ⚠ {capMessage} — refine your query with a tighter filter or LIMIT clause for more specific results.
        </div>
      )}
    </div>
  )
}
