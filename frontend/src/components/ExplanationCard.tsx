interface Props {
  explanation: string
  success: boolean
  error: string | null
  hasData: boolean
}

export function ExplanationCard({ explanation, success, error, hasData }: Props) {
  if (error && !success) {
    return (
      <div className="rounded-xl border border-red-900/50 bg-red-950/30 px-5 py-4">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-red-400 text-base">⚠</span>
          <p className="text-sm font-medium text-red-400">Query failed</p>
        </div>
        <p className="text-sm text-red-300/70 leading-relaxed">{explanation}</p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] px-5 py-4 relative overflow-hidden">
      {/* Subtle left accent bar */}
      <div className="absolute left-0 top-3 bottom-3 w-0.5 rounded-full bg-gradient-to-b from-violet-500 to-violet-800" />

      <div className="pl-3">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-xs font-semibold text-violet-400 uppercase tracking-widest">Answer</span>
          {hasData && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-violet-950/60 border border-violet-800/50 text-violet-400">
              with data
            </span>
          )}
        </div>
        <p className="text-sm text-slate-200 leading-relaxed">{explanation}</p>
      </div>
    </div>
  )
}
