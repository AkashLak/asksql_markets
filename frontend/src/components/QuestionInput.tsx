interface Props {
  onSubmit: (question: string) => void
  loading: boolean
}

const EXAMPLES = [
  'What are the top 5 stocks by closing price today?',
  'Which sector has the highest average revenue in 2024?',
  'Show dividend history for Apple',
  'Which companies had a profit margin above 30% in 2023?',
  'What was the average daily volume for Tesla in 2023?',
]

export function QuestionInput({ onSubmit, loading }: Props) {
  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const q = (form.elements.namedItem('question') as HTMLInputElement).value.trim()
    if (q) onSubmit(q)
  }

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          name="question"
          type="text"
          placeholder="Ask a question about S&P 500 data..."
          disabled={loading}
          className="flex-1 px-4 py-3 rounded-lg bg-slate-800 border border-slate-600
                     text-slate-100 placeholder-slate-400 text-sm
                     focus:outline-none focus:border-violet-500 focus:ring-1 focus:ring-violet-500
                     disabled:opacity-50 disabled:cursor-not-allowed"
          autoComplete="off"
          autoFocus
        />
        <button
          type="submit"
          disabled={loading}
          className="px-5 py-3 rounded-lg bg-violet-600 hover:bg-violet-500 active:bg-violet-700
                     text-white text-sm font-medium transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? 'Running…' : 'Ask'}
        </button>
      </form>

      {/* Example questions */}
      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => onSubmit(ex)}
            disabled={loading}
            className="text-xs px-3 py-1.5 rounded-full border border-slate-600 text-slate-400
                       hover:border-violet-500 hover:text-violet-300 transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}
