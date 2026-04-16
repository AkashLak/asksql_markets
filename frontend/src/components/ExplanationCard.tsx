interface Props {
  explanation: string
  success: boolean
  error: string | null
}

export function ExplanationCard({ explanation, success, error }: Props) {
  if (error && !success) {
    return (
      <div className="rounded-lg border border-red-700/50 bg-red-900/20 px-4 py-3">
        <p className="text-sm font-medium text-red-400 mb-1">Query failed</p>
        <p className="text-sm text-red-300/80">{explanation}</p>
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/50 px-4 py-3">
      <p className="text-xs font-medium text-slate-400 uppercase tracking-wider mb-2">Answer</p>
      <p className="text-sm text-slate-200 leading-relaxed">{explanation}</p>
    </div>
  )
}
