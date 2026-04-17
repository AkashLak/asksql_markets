import { useRef } from 'react'

interface Props {
  onSubmit: (question: string) => void
  loading: boolean
  hero: boolean
}

const EXAMPLES = [
  'What are the top 5 stocks by closing price today?',
  'Which sector has the highest average revenue in 2024?',
  'Show dividend history for Apple',
  'Which companies had a profit margin above 30% in 2023?',
  'How many companies reported a net loss in 2023?',
]

export function QuestionInput({ onSubmit, loading, hero }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const q = inputRef.current?.value.trim() ?? ''
    if (q) onSubmit(q)
  }

  function handleExample(ex: string) {
    if (inputRef.current) inputRef.current.value = ex
    onSubmit(ex)
  }

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit}>
        <div className={`relative flex items-center rounded-xl border transition-colors
          ${hero
            ? 'border-white/10 bg-white/[0.04] hover:border-violet-600/50 focus-within:border-violet-500 focus-within:bg-white/[0.06]'
            : 'border-white/[0.08] bg-white/[0.03] hover:border-violet-600/40 focus-within:border-violet-500/60'
          }`}
        >
          <span className="pl-4 text-slate-500 flex-shrink-0">
            <svg xmlns="http://www.w3.org/2000/svg" className={hero ? 'w-5 h-5' : 'w-4 h-4'} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
          </span>
          <input
            ref={inputRef}
            name="question"
            type="text"
            placeholder="Ask a question about S&P 500 data…"
            disabled={loading}
            className={`flex-1 bg-transparent text-slate-100 placeholder-slate-500 outline-none
              disabled:opacity-50 disabled:cursor-not-allowed
              ${hero ? 'px-4 py-4 text-base' : 'px-3 py-3 text-sm'}`}
            autoComplete="off"
            autoFocus={hero}
          />
          <button
            type="submit"
            disabled={loading}
            className={`flex-shrink-0 mr-1.5 rounded-lg bg-violet-600 hover:bg-violet-500 active:bg-violet-700
              text-white font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed
              ${hero ? 'px-5 py-2.5 text-sm' : 'px-4 py-2 text-xs'}`}
          >
            {loading ? (
              <span className="flex items-center gap-1.5">
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Running
              </span>
            ) : 'Ask'}
          </button>
        </div>
      </form>

      {/* Example chips */}
      <div className={`flex flex-wrap gap-2 ${hero ? 'mt-4' : 'mt-2.5'}`}>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => handleExample(ex)}
            disabled={loading}
            className={`rounded-full border border-white/[0.08] text-slate-400
              hover:border-violet-500/50 hover:text-violet-300 hover:bg-violet-950/40
              transition-all disabled:opacity-40 disabled:cursor-not-allowed
              ${hero ? 'text-xs px-3 py-1.5' : 'text-xs px-2.5 py-1'}`}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}
