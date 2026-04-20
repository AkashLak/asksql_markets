interface Props {
  explanation: string
  success: boolean
  error: string | null
}

// Bold any numbers / dollar amounts in the explanation text
function highlightNumbers(text: string): React.ReactNode[] {
  const parts = text.split(/(\$?[\d,]+(?:\.\d+)?(?:\s?[BMK%])?(?:\s?(?:billion|million|trillion))?)/g)
  return parts.map((part, i) => {
    const isNum = /^\$?[\d,]+/.test(part) && part.replace(/[,$.\s]/g, '').length >= 2
    return isNum
      ? <span key={i} className="text-violet-300 font-semibold tabular-nums">{part}</span>
      : part
  })
}

export function AnswerCard({ explanation, success, error }: Props) {
  if (error && !success) {
    return (
      <div className="glass-card rounded-2xl px-5 py-4 border border-red-900/40">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-base">⚠️</span>
          <p className="text-sm font-semibold text-red-400">Query failed</p>
        </div>
        <p className="text-sm text-red-300/70 leading-relaxed">{explanation}</p>
      </div>
    )
  }

  return (
    <div className="glass-card rounded-2xl px-5 py-4 relative">
      {/* Left gradient accent */}
      <div className="absolute left-0 inset-y-0 w-[3px] rounded-r-full
                      bg-gradient-to-b from-violet-400 via-indigo-500 to-violet-700" />

      <div className="pl-4">
        <div className="flex items-center gap-2 mb-2.5">
          <span className="text-base">✦</span>
          <span className="text-xs font-semibold text-violet-400 uppercase tracking-widest">Answer</span>
        </div>
        <p className="text-[15px] text-slate-200 leading-relaxed">
          {highlightNumbers(explanation)}
        </p>
      </div>
    </div>
  )
}
