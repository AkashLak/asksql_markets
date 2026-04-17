import { useRef } from 'react'
import { motion } from 'framer-motion'

interface Props {
  onSubmit: (question: string) => void
  loading: boolean
  autoFocus?: boolean
  defaultValue?: string
}

const EXAMPLES = [
  'Top 5 stocks by closing price today?',
  'Highest revenue sector in 2024?',
  'Apple dividend history',
  'Companies with profit margin above 30%?',
  'Average Tesla volume in 2023?',
]

export function SearchBar({ onSubmit, loading, autoFocus, defaultValue }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = inputRef.current?.value.trim() ?? ''
    if (q && !loading) onSubmit(q)
  }

  function handleExample(ex: string) {
    if (inputRef.current) inputRef.current.value = ex
    if (!loading) onSubmit(ex)
  }

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit}>
        <div
          className="input-glow relative flex items-center rounded-2xl border border-white/[0.1]
                     bg-white/[0.05] transition-all duration-200
                     hover:border-white/[0.18] hover:bg-white/[0.07]"
        >
          <span className="pl-4 text-slate-500 flex-shrink-0">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
          </span>

          <input
            ref={inputRef}
            type="text"
            defaultValue={defaultValue}
            placeholder="Ask anything about S&P 500 data…"
            disabled={loading}
            autoFocus={autoFocus}
            autoComplete="off"
            className="flex-1 bg-transparent px-3 py-5 text-sm text-slate-100 placeholder-slate-500
                       outline-none disabled:opacity-50 disabled:cursor-not-allowed"
          />

          <motion.button
            type="submit"
            disabled={loading}
            whileHover={{ scale: 1.04 }}
            whileTap={{ scale: 0.97 }}
            className="flex-shrink-0 mr-2 flex items-center gap-2 px-5 py-2.5 rounded-xl
                       bg-violet-600 hover:bg-violet-500 text-white text-sm font-medium
                       transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>Running</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
                </svg>
                <span>Ask</span>
              </>
            )}
          </motion.button>
        </div>
      </form>

      {/* Example chips */}
      <div className="mt-3 flex flex-wrap gap-2">
        {EXAMPLES.map((ex) => (
          <motion.button
            key={ex}
            onClick={() => handleExample(ex)}
            disabled={loading}
            whileHover={{ scale: 1.04, y: -1 }}
            whileTap={{ scale: 0.97 }}
            className="text-xs px-3 py-1.5 rounded-full border border-white/[0.1] bg-white/[0.04]
                       text-slate-400 hover:border-violet-500/60 hover:text-violet-300
                       hover:bg-violet-950/50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {ex}
          </motion.button>
        ))}
      </div>
    </div>
  )
}
