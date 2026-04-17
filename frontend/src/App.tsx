import { useState } from 'react'
import { askQuestion } from './api'
import type { AskResponse } from './types'
import { QuestionInput } from './components/QuestionInput'
import { SqlDisplay } from './components/SqlDisplay'
import { ResultsTable } from './components/ResultsTable'
import { ExplanationCard } from './components/ExplanationCard'

type Status = 'idle' | 'loading' | 'done' | 'error'

// Simple guard: catch greetings and very short non-data phrases before hitting the API
const NON_QUERY_RE = /^(hi+|hello|hey|sup|yo|test|ok|okay|thanks|bye|lol|hm+|what|why|how)\s*[!?.]*$/i

function isNonDataQuery(q: string): boolean {
  return NON_QUERY_RE.test(q.trim()) || q.trim().split(/\s+/).length < 2
}

export default function App() {
  const [status, setStatus] = useState<Status>('idle')
  const [result, setResult] = useState<AskResponse | null>(null)
  const [fetchError, setFetchError] = useState<string | null>(null)
  const [lastQuestion, setLastQuestion] = useState<string>('')

  async function handleQuestion(question: string) {
    if (isNonDataQuery(question)) {
      setLastQuestion(question)
      setResult(null)
      setFetchError(null)
      setStatus('done')
      // Synthesise a friendly "can't answer" response without calling the API
      setResult({
        sql: null,
        columns: [],
        results: [],
        explanation: "I can only answer questions about S&P 500 data — try asking about stock prices, revenues, dividends, or sectors.",
        success: true,
        error: null,
      })
      return
    }

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

  const isIdle = status === 'idle'

  return (
    <div className={`min-h-screen flex flex-col ${isIdle ? 'hero-bg grid-bg' : 'bg-[#07080f]'}`}>

      {/* ── Header (results mode only) ── */}
      {!isIdle && (
        <header className="border-b border-white/[0.06] px-6 py-3 sticky top-0 z-10 bg-[#07080f]/90 backdrop-blur">
          <div className="max-w-3xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-100 tracking-tight">
                AskSQL <span className="gradient-text">Markets</span>
              </span>
            </div>
            <span className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/50">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
              Live
            </span>
          </div>
        </header>
      )}

      {/* ── Idle hero ── */}
      {isIdle && (
        <div className="flex-1 flex flex-col items-center justify-center px-6 pt-16 pb-24">
          <div className="w-full max-w-2xl flex flex-col items-center gap-6">

            {/* Badge */}
            <span className="text-xs px-3 py-1 rounded-full bg-violet-950/60 border border-violet-700/40 text-violet-300">
              S&amp;P 500 · Real financial data
            </span>

            {/* Title */}
            <div className="text-center space-y-2">
              <h1 className="text-5xl font-bold tracking-tight">
                <span className="gradient-text">AskSQL</span>{' '}
                <span className="text-slate-100">Markets</span>
              </h1>
              <p className="text-slate-400 text-lg">
                Ask anything about S&amp;P 500 companies in plain English.
              </p>
            </div>

            {/* Input */}
            <div className="w-full">
              <QuestionInput onSubmit={handleQuestion} loading={false} hero />
            </div>

            {/* Stats row */}
            <div className="flex items-center gap-6 text-xs text-slate-500">
              {[
                ['503', 'companies'],
                ['5 yrs', 'price history'],
                ['~49k', 'dividend records'],
                ['4 yrs', 'financials'],
              ].map(([val, label]) => (
                <div key={label} className="text-center">
                  <div className="text-slate-300 font-semibold">{val}</div>
                  <div>{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Results mode ── */}
      {!isIdle && (
        <main className="flex-1 max-w-3xl w-full mx-auto px-6 py-6 flex flex-col gap-5">

          {/* Input bar */}
          <QuestionInput onSubmit={handleQuestion} loading={status === 'loading'} hero={false} />

          {/* Loading */}
          {status === 'loading' && (
            <div className="flex flex-col items-center justify-center py-16 gap-4">
              <div className="flex gap-1.5">
                <span className="loading-dot w-2 h-2 rounded-full bg-violet-500" />
                <span className="loading-dot w-2 h-2 rounded-full bg-violet-500" />
                <span className="loading-dot w-2 h-2 rounded-full bg-violet-500" />
              </div>
              <p className="text-xs text-slate-500">Generating SQL and querying database…</p>
            </div>
          )}

          {/* Network error */}
          {status === 'error' && fetchError && (
            <div className="card rounded-xl px-5 py-4 border-red-900/50">
              <p className="text-sm font-medium text-red-400 mb-1">Connection error</p>
              <p className="text-sm text-red-300/70">{fetchError}</p>
            </div>
          )}

          {/* Results */}
          {status === 'done' && result && (
            <div className="flex flex-col gap-4">
              {/* Question echo */}
              <div className="flex items-start gap-2.5">
                <div className="mt-0.5 w-5 h-5 rounded-full bg-violet-600/30 border border-violet-500/40 flex items-center justify-center flex-shrink-0">
                  <span className="text-[10px] text-violet-300 font-bold">Q</span>
                </div>
                <p className="text-slate-200 text-sm leading-relaxed">{lastQuestion}</p>
              </div>

              <ExplanationCard
                explanation={result.explanation}
                success={result.success}
                error={result.error}
                hasData={result.columns.length > 0}
              />

              {result.sql && <SqlDisplay sql={result.sql} />}

              {result.columns.length > 0 && (
                <ResultsTable columns={result.columns} results={result.results} />
              )}
            </div>
          )}
        </main>
      )}
    </div>
  )
}
