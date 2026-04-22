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

const LOADING_MSGS = ['Generating SQL…', 'Querying financial data…', 'Analyzing results…', 'Almost there…']

const fade = {
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.24 } },
  exit:    { opacity: 0, y: -6, transition: { duration: 0.16 } },
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p style={{
      fontSize: '10px',
      letterSpacing: '0.12em',
      textTransform: 'uppercase',
      color: 'rgba(255,255,255,0.25)',
      marginBottom: '10px',
    }}>
      {children}
    </p>
  )
}

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
    <div style={{ background: '#0a0a0a', minHeight: '100vh' }}>
      <AnimatePresence mode="wait">

        {/* ── IDLE: landing ── */}
        {status === 'idle' && (
          <motion.div key="idle" {...fade} style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0 24px',
          }}>
            <div style={{ width: '100%', maxWidth: '600px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>

              {/* Wordmark */}
              <p style={{ fontSize: '10px', letterSpacing: '0.16em', color: 'rgba(255,255,255,0.3)', textTransform: 'uppercase', marginBottom: '28px' }}>
                S&amp;P 500 · Real Financial Data · AI-Powered
              </p>

              {/* Logo */}
              <h1 style={{ fontSize: '52px', fontWeight: 500, letterSpacing: '-2px', lineHeight: 1, marginBottom: '16px' }}>
                <span style={{ color: '#ffffff' }}>Ask</span>
                <span style={{ color: 'rgba(255,255,255,0.35)' }}>SQL</span>
              </h1>

              {/* Tagline */}
              <p style={{ fontSize: '15px', color: 'rgba(255,255,255,0.4)', marginBottom: '40px', textAlign: 'center', lineHeight: 1.5 }}>
                Query S&amp;P 500 data in plain English. No SQL required.
              </p>

              {/* Search bar */}
              <div style={{ width: '100%', marginBottom: '48px' }}>
                <SearchBar onSubmit={handleQuestion} loading={false} autoFocus />
              </div>

              {/* Divider + stats */}
              <div style={{ width: '100%', borderTop: '0.5px solid rgba(255,255,255,0.08)', paddingTop: '32px' }}>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '48px' }}>
                  {([['503', 'companies'], ['5 yrs', 'price history'], ['~49k', 'dividends'], ['4 yrs', 'financials']] as const).map(([v, l]) => (
                    <div key={l} style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '18px', fontWeight: 500, color: 'rgba(255,255,255,0.7)', letterSpacing: '-0.5px' }}>{v}</div>
                      <div style={{ fontSize: '11px', color: 'rgba(255,255,255,0.28)', marginTop: '5px' }}>{l}</div>
                    </div>
                  ))}
                </div>
              </div>

            </div>
          </motion.div>
        )}

        {/* ── LOADING ── */}
        {status === 'loading' && (
          <motion.div key="loading" {...fade} style={{
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            padding: '28px 24px',
          }}>
            <div style={{ width: '100%', maxWidth: '680px' }}>
              <SearchBar onSubmit={handleQuestion} loading={true} defaultValue={lastQuestion} />
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '14px', paddingTop: '100px' }}>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '6px' }}>
                  <span className="dot-1" style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'rgba(255,255,255,0.45)', display: 'block' }} />
                  <span className="dot-2" style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'rgba(255,255,255,0.45)', display: 'block' }} />
                  <span className="dot-3" style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'rgba(255,255,255,0.45)', display: 'block' }} />
                </div>
                <AnimatePresence mode="wait">
                  <motion.p key={msgIdx}
                    initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.18 }}
                    style={{ fontSize: '13px', color: 'rgba(255,255,255,0.35)' }}
                  >
                    {LOADING_MSGS[msgIdx]}
                  </motion.p>
                </AnimatePresence>
                <p style={{ fontSize: '12px', color: 'rgba(255,255,255,0.18)', maxWidth: '380px', textAlign: 'center' }}>
                  {lastQuestion}
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {/* ── RESULTS / ERROR ── */}
        {(status === 'done' || status === 'error') && (
          <motion.div key="results" {...fade} style={{ minHeight: '100vh' }}>

            {/* Sticky top bar */}
            <div style={{
              position: 'sticky', top: 0, zIndex: 20,
              background: '#0a0a0a',
              borderBottom: '0.5px solid rgba(255,255,255,0.08)',
              padding: '10px 24px',
            }}>
              <div style={{ maxWidth: '680px', margin: '0 auto', display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexShrink: 0 }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#4ade80', display: 'block' }} />
                  <span style={{ fontSize: '11px', color: 'rgba(255,255,255,0.35)', letterSpacing: '0.04em' }}>Live</span>
                </div>
                <div style={{ flex: 1 }}>
                  <SearchBar onSubmit={handleQuestion} loading={false} />
                </div>
              </div>
            </div>

            {/* Page content */}
            <div style={{ maxWidth: '680px', margin: '0 auto', padding: '40px 24px 100px' }}>

              {/* Error state */}
              {status === 'error' && fetchError && (
                <div style={{
                  background: 'rgba(255,255,255,0.03)',
                  border: '0.5px solid rgba(255,255,255,0.08)',
                  borderRadius: '8px',
                  padding: '16px 20px',
                }}>
                  <p style={{ fontSize: '11px', color: 'rgba(255,255,255,0.3)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Connection error</p>
                  <p style={{ fontSize: '14px', color: 'rgba(255,255,255,0.55)' }}>{fetchError}</p>
                </div>
              )}

              {/* Results */}
              {status === 'done' && result && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>

                  {/* Question bubble */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <div style={{
                      maxWidth: '480px',
                      background: 'rgba(255,255,255,0.05)',
                      border: '0.5px solid rgba(255,255,255,0.1)',
                      borderRadius: '10px',
                      padding: '10px 16px',
                      fontSize: '14px',
                      color: 'rgba(255,255,255,0.65)',
                      lineHeight: 1.5,
                    }}>
                      {lastQuestion}
                    </div>
                  </div>

                  {/* Answer */}
                  <section>
                    <SectionLabel>Answer</SectionLabel>
                    <AnswerCard explanation={result.explanation} success={result.success} error={result.error} />
                  </section>

                  {/* Chart */}
                  {result.columns.length > 0 && result.results.length >= 2 && (
                    <section>
                      <DataChart columns={result.columns} results={result.results} question={lastQuestion} />
                    </section>
                  )}

                  {/* SQL */}
                  {result.sql && (
                    <section>
                      <SectionLabel>Generated SQL</SectionLabel>
                      <SqlDisplay sql={result.sql} />
                    </section>
                  )}

                  {/* Table */}
                  {result.columns.length > 0 && (
                    <section>
                      <SectionLabel>Results</SectionLabel>
                      <ResultsTable columns={result.columns} results={result.results} />
                    </section>
                  )}

                </div>
              )}
            </div>
          </motion.div>
        )}

      </AnimatePresence>
    </div>
  )
}
