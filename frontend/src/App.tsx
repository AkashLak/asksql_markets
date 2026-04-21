import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { askQuestion } from './api'
import type { AskResponse } from './types'
import { SearchBar } from './components/SearchBar'
import { SqlDisplay } from './components/SqlDisplay'
import { ResultsTable } from './components/ResultsTable'
import { AnswerCard } from './components/AnswerCard'
import { DataChart } from './components/DataChart'

type Status = 'idle' | 'loading' | 'done' | 'error'

const NON_QUERY_RE = /^(hi+|hello|hey|sup|yo|test|ok|okay|thanks|bye|lol|hm+)\s*[!?.]*$/i
function isNonDataQuery(q: string) {
  return NON_QUERY_RE.test(q.trim()) || q.trim().split(/\s+/).length < 2
}

const viewAnim = {
  initial: { opacity: 0, y: 14 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.32 } },
  exit:    { opacity: 0, y: -8, transition: { duration: 0.18 } },
}

const LOADING_MSGS = ['Generating SQL…', 'Querying financial data…', 'Analyzing results…', 'Almost there…']

export default function App() {
  const [status, setStatus]             = useState<Status>('idle')
  const [result, setResult]             = useState<AskResponse | null>(null)
  const [fetchError, setFetchError]     = useState<string | null>(null)
  const [lastQuestion, setLastQuestion] = useState('')
  const [msgIdx, setMsgIdx]             = useState(0)

  useEffect(() => {
    if (status !== 'loading') return
    const id = setInterval(() => setMsgIdx(i => (i + 1) % LOADING_MSGS.length), 1600)
    return () => clearInterval(id)
  }, [status])

  async function handleQuestion(question: string) {
    if (isNonDataQuery(question)) {
      setLastQuestion(question)
      setResult({ sql: null, columns: [], results: [], explanation: "I can only answer questions about S&P 500 data — try asking about stock prices, revenues, dividends, or sectors.", success: true, error: null })
      setStatus('done')
      return
    }
    setStatus('loading')
    setResult(null)
    setFetchError(null)
    setLastQuestion(question)
    setMsgIdx(0)
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
    <div className="min-h-screen relative bg-[#05050e]">
      {/* Animated blobs */}
      <div className="fixed inset-0 overflow-hidden z-0">
        <div className="blob blob-1" />
        <div className="blob blob-2" />
        <div className="blob blob-3" />
      </div>
      {/* Grid overlay */}
      <div className="grid-overlay" />

      <div className="relative z-10 min-h-screen flex flex-col">

        {/* Compact header - shown on non-idle */}
        <AnimatePresence>
          {status !== 'idle' && (
            <motion.header
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0, transition: { duration: 0.25 } }}
              exit={{ opacity: 0 }}
              className="sticky top-0 z-20 border-b border-white/[0.07] bg-[#05050e]/85 backdrop-blur"
            >
              <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
                <span className="text-sm font-bold text-slate-100 tracking-tight">
                  AskSQL <span className="gradient-text">Markets</span>
                </span>
                <span className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live
                </span>
              </div>
            </motion.header>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">

          {/* --- IDLE --- */}
          {status === 'idle' && (
            <motion.div key="idle" {...viewAnim}
              className="min-h-screen flex flex-col items-center justify-center px-6"
            >
              <div className="w-full max-w-3xl flex flex-col items-center gap-6 text-center">

                <motion.span
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1, transition: { delay: 0.05 } }}
                  className="text-xs px-3 py-1 rounded-full bg-violet-950/70 border border-violet-600/40 text-violet-300 tracking-wide"
                >
                  S&amp;P 500 · Real financial data · AI-powered
                </motion.span>

                <motion.div
                  initial={{ opacity: 0, y: 18 }}
                  animate={{ opacity: 1, y: 0, transition: { delay: 0.1, duration: 0.45 } }}
                >
                  <h1 className="text-8xl font-black tracking-tight leading-[1.05]">
                    <span className="gradient-text">AskSQL</span>
                    <br />
                    <span className="text-slate-200 text-6xl font-bold">Markets</span>
                  </h1>
                  <p className="mt-4 text-slate-500 text-base">
                    Query S&amp;P 500 data in plain English. No SQL required.
                  </p>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0, transition: { delay: 0.2, duration: 0.4 } }}
                  className="w-full mt-10"
                >
                  <SearchBar onSubmit={handleQuestion} loading={false} autoFocus />
                </motion.div>

                {/* Stats row */}
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1, transition: { delay: 0.38 } }}
                  className="w-full"
                >
                  <div className="border-t border-white/[0.07] pt-6 mt-8 flex justify-center gap-12">
                    {[['503', 'companies'], ['5 yrs', 'price history'], ['~49k', 'dividend records'], ['4 yrs', 'financials']].map(([v, l]) => (
                      <div key={l} className="text-center">
                        <div className="text-white font-bold text-2xl tracking-tight">{v}</div>
                        <div className="text-slate-500 text-sm mt-1">{l}</div>
                      </div>
                    ))}
                  </div>
                </motion.div>
              </div>
            </motion.div>
          )}

          {/* --- LOADING --- */}
          {status === 'loading' && (
            <motion.div key="loading" {...viewAnim}
              className="min-h-screen flex flex-col w-full items-center px-6 pt-8 pb-12"
            >
              <div className="w-full max-w-4xl flex flex-col gap-6">
                <SearchBar onSubmit={handleQuestion} loading={true} defaultValue={lastQuestion} />
                <div className="flex flex-col items-center justify-center gap-4 py-14">
                  <div className="flex items-end gap-2">
                    <span className="dot-1 w-3 h-3 rounded-full bg-violet-500" />
                    <span className="dot-2 w-3 h-3 rounded-full bg-violet-400" />
                    <span className="dot-3 w-3 h-3 rounded-full bg-violet-300" />
                  </div>
                  <AnimatePresence mode="wait">
                    <motion.p key={msgIdx}
                      initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -5 }} transition={{ duration: 0.22 }}
                      className="text-sm text-slate-400"
                    >
                      {LOADING_MSGS[msgIdx]}
                    </motion.p>
                  </AnimatePresence>
                  <p className="text-xs text-slate-600 max-w-sm text-center">{lastQuestion}</p>
                </div>
              </div>
            </motion.div>
          )}

          {/* --- RESULTS --- */}
          {(status === 'done' || status === 'error') && (
            <motion.div key="results" {...viewAnim}
              className="min-h-screen flex flex-col items-center w-full pt-8 pb-24"
            >
              <div className="w-full max-w-5xl mx-auto flex flex-col gap-5 px-8">

                <SearchBar onSubmit={handleQuestion} loading={false} />

                {status === 'error' && fetchError && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                    className="glass-card rounded-2xl px-5 py-4"
                  >
                    <p className="text-sm font-semibold text-red-400 mb-1">Connection error</p>
                    <p className="text-sm text-red-300/60">{fetchError}</p>
                  </motion.div>
                )}

                {status === 'done' && result && (
                  <>
                    <motion.div
                      initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: 0.04 }}
                      className="flex justify-end"
                    >
                      <div className="max-w-xl bg-violet-600/20 border border-violet-500/30 rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-slate-200">
                        {lastQuestion}
                      </div>
                    </motion.div>

                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                      <AnswerCard explanation={result.explanation} success={result.success} error={result.error} />
                    </motion.div>

                    {result.columns.length > 0 && result.results.length >= 2 && (
                      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}>
                        <DataChart columns={result.columns} results={result.results} question={lastQuestion} />
                      </motion.div>
                    )}

                    {result.sql && (
                      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22 }}>
                        <SqlDisplay sql={result.sql} />
                      </motion.div>
                    )}

                    {result.columns.length > 0 && (
                      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.28 }}>
                        <ResultsTable columns={result.columns} results={result.results} />
                      </motion.div>
                    )}
                  </>
                )}
              </div>
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  )
}
