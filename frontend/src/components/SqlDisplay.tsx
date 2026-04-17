import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface Props { sql: string }

export function SqlDisplay({ sql }: Props) {
  const [open, setOpen]     = useState(false)
  const [copied, setCopied] = useState(false)

  function copy(e: React.MouseEvent) {
    e.stopPropagation()
    navigator.clipboard.writeText(sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      {/* Toggle header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-3 hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <span className="flex gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
            <span className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
          </span>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Generated SQL</span>
        </div>
        <div className="flex items-center gap-2">
          <motion.button
            onClick={copy}
            whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
            className={`flex items-center gap-1.5 text-xs px-3 py-1 rounded-lg transition-all
              ${copied
                ? 'bg-emerald-950/60 border border-emerald-800/50 text-emerald-400'
                : 'border border-white/[0.08] text-slate-400 hover:text-white hover:border-white/20'
              }`}
          >
            {copied ? (
              <><svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>Copied</>
            ) : (
              <><svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}><path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 0 1-.75.75H9a.75.75 0 0 1-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 0 1-2.25 2.25H6.75A2.25 2.25 0 0 1 4.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 0 1 1.927-.184" /></svg>Copy</>
            )}
          </motion.button>
          <motion.span
            animate={{ rotate: open ? 180 : 0 }}
            transition={{ duration: 0.2 }}
            className="text-slate-500"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
            </svg>
          </motion.span>
        </div>
      </button>

      {/* Collapsible content */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            style={{ overflow: 'hidden' }}
          >
            <div className="border-t border-white/[0.06]">
              <pre className="p-5 text-sm text-emerald-300/90 bg-black/20 overflow-x-auto leading-relaxed font-mono whitespace-pre-wrap break-words">
                {sql}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
