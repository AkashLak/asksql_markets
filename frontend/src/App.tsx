import { useState } from 'react'
import { askQuestion } from './api'
import type { AskResponse } from './types'
import { QuestionInput } from './components/QuestionInput'
import { SqlDisplay } from './components/SqlDisplay'
import { ResultsTable } from './components/ResultsTable'
import { ExplanationCard } from './components/ExplanationCard'

type Status = 'idle' | 'loading' | 'done' | 'error'

export default function App() {
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<AskResponse | null>(null)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [lastQuestion, setLastQuestion] = useState<string>('')

  async function handleQuestion(question: string) {
    setStatus('loading')
    setResult(null)
    setFetchError(null)
    setLastQuestion(question)
    try {
      const data = await askQuestion(question)
      setResult(data)
      setStatus('done')
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : 'Unknown error')
      setStatus('error')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-100 tracking-tight">
              AskSQL <span className="text-violet-400">Markets</span>
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">Natural language queries over S&amp;P 500 data</p>
          </div>
          <span className="text-xs px-2 py-1 rounded-full bg-emerald-900/40 text-emerald-400 border border-emerald-700/50">
            Live
          </span>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-6 py-8 flex flex-col gap-6">
        {/* Input */}
        <QuestionInput onSubmit={handleQuestion} loading={status === 'loading'} />

        {/* Loading */}
        {status === 'loading' && (
          <div className="flex items-center gap-3 text-sm text-slate-400">
            <span className="inline-block w-4 h-4 border-2 border-slate-600 border-t-violet-500 rounded-full animate-spin" />
            Generating SQL and querying the database…
          </div>
        )}

        {/* Fetch-level error (network / 400 / 500) */}
        {status === 'error' && fetchError && (
          <div className="rounded-lg border border-red-700/50 bg-red-900/20 px-4 py-3 text-sm text-red-300">
            {fetchError}
          </div>
        )}

        {/* Results */}
        {status === 'done' && result && (
          <div className="flex flex-col gap-4">
            {/* Question echo */}
            <p className="text-sm text-slate-400">
              <span className="text-slate-500">Q:</span>{' '}
              <span className="text-slate-200">{lastQuestion}</span>
            </p>

            {/* Explanation */}
            <ExplanationCard
              explanation={result.explanation}
              success={result.success}
              error={result.error}
            />

            {/* SQL */}
            {result.sql && <SqlDisplay sql={result.sql} />}

            {/* Table */}
            {result.columns.length > 0 && (
              <ResultsTable columns={result.columns} results={result.results} />
            )}
          </div>
        )}

        {/* Empty state */}
        {status === 'idle' && (
          <div className="flex-1 flex flex-col items-center justify-center py-16 text-center gap-3">
            <div className="text-4xl">📊</div>
            <p className="text-slate-400 text-sm max-w-sm">
              Ask any question about S&amp;P 500 companies, stock prices, financials, or dividends.
              The AI will generate SQL and query the database for you.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
