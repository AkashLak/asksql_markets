interface Props {
  sql: string
}

export function SqlDisplay({ sql }: Props) {
  function copy() {
    navigator.clipboard.writeText(sql)
  }

  return (
    <div className="rounded-lg border border-slate-700 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-800 border-b border-slate-700">
        <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Generated SQL</span>
        <button
          onClick={copy}
          className="text-xs text-slate-400 hover:text-slate-200 transition-colors px-2 py-1 rounded hover:bg-slate-700"
        >
          Copy
        </button>
      </div>
      <pre className="p-4 text-sm text-emerald-300 bg-slate-900 overflow-x-auto leading-relaxed font-mono whitespace-pre-wrap break-words">
        {sql}
      </pre>
    </div>
  )
}
