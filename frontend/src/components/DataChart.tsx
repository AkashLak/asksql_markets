import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  Cell, Label,
} from 'recharts'

const VIOLET_PALETTE = ['#7c3aed', '#6d28d9', '#8b5cf6', '#a78bfa', '#5b21b6', '#c4b5fd', '#9333ea']

interface ChartConfig {
  type: 'bar' | 'line'
  xIndex: number
  yIndex: number
  xKey: string
  yKey: string
}

function detectChart(
  columns: string[],
  results: (string | number | null)[][]
): ChartConfig | null {
  if (results.length < 2 || results.length > 40) return null

  const colMeta = columns.map((col, i) => {
    const vals = results.map(r => r[i]).filter(v => v !== null && v !== '')
    const numericCount = vals.filter(v => typeof v === 'number').length
    return { col, i, isNumeric: numericCount / Math.max(vals.length, 1) > 0.8 }
  })

  const numCols = colMeta.filter(c => c.isNumeric)
  const catCols = colMeta.filter(c => !c.isNumeric)
  if (numCols.length === 0 || catCols.length === 0) return null

  const xCol = catCols[0]
  const yCol = numCols[0]
  const hasDate = /date|year|month|period|quarter|day/i.test(xCol.col)

  return { type: hasDate ? 'line' : 'bar', xIndex: xCol.i, yIndex: yCol.i, xKey: xCol.col, yKey: yCol.col }
}

function formatValue(v: number): string {
  if (Math.abs(v) >= 1e12) return (v / 1e12).toFixed(1) + 'T'
  if (Math.abs(v) >= 1e9)  return (v / 1e9).toFixed(1) + 'B'
  if (Math.abs(v) >= 1e6)  return (v / 1e6).toFixed(1) + 'M'
  if (Math.abs(v) >= 1e3)  return (v / 1e3).toFixed(1) + 'K'
  return v.toFixed(2).replace(/\.?0+$/, '')
}

function truncateLabel(s: string): string {
  return s.length > 12 ? s.slice(0, 10) + '…' : s
}

// Derive a readable chart title from the column names
function chartTitle(xKey: string, yKey: string): string {
  const fmt = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  return `${fmt(yKey)} by ${fmt(xKey)}`
}

const tooltipStyle = {
  contentStyle: {
    background: '#0a0818',
    border: '1px solid rgba(139,92,246,0.25)',
    borderRadius: '10px',
    fontSize: '12px',
    color: '#e2e8f0',
    boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
  },
  labelStyle: { color: '#a78bfa', fontWeight: 700, marginBottom: 2 },
  cursor: { fill: 'rgba(109,40,217,0.08)' },
}

interface Props {
  columns: string[]
  results: (string | number | null)[][]
  question: string
}

export function DataChart({ columns, results, question: _question }: Props) {
  const cfg = detectChart(columns, results)
  if (!cfg) return null

  const dataRows = results.filter(r => typeof r[0] !== 'string' || !String(r[0]).startsWith('…'))
  const chartData = dataRows.map(row => ({
    name: String(row[cfg.xIndex] ?? ''),
    value: typeof row[cfg.yIndex] === 'number' ? (row[cfg.yIndex] as number) : 0,
  }))

  const title = chartTitle(cfg.xKey, cfg.yKey)
  const xLabel = cfg.xKey.replace(/_/g, ' ')
  const yLabel = cfg.yKey.replace(/_/g, ' ')

  const axisProps = {
    stroke: 'transparent',
    tick: { fill: '#4b5563', fontSize: 11 },
    tickLine: false,
    axisLine: false,
  }

  return (
    <div className="glass-card rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.07]">
        <div className="flex items-center gap-2.5">
          <span className="text-sm">{cfg.type === 'line' ? '📉' : '📊'}</span>
          <span className="text-sm font-semibold text-slate-200">{title}</span>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-md bg-violet-950/60 border border-violet-800/40 text-violet-400">
          {cfg.type === 'line' ? 'trend' : 'bar chart'}
        </span>
      </div>

      <div className="px-3 pt-5 pb-4">
        <ResponsiveContainer width="100%" height={300}>
          {cfg.type === 'line' ? (
            <LineChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 36 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="name" {...axisProps} tickFormatter={truncateLabel} interval="preserveStartEnd">
                <Label value={xLabel} offset={-16} position="insideBottom" style={{ fill: '#4b5563', fontSize: 11 }} />
              </XAxis>
              <YAxis {...axisProps} tickFormatter={formatValue} width={52}>
                <Label value={yLabel} angle={-90} position="insideLeft" style={{ fill: '#4b5563', fontSize: 11 }} />
              </YAxis>
              <Tooltip {...tooltipStyle} formatter={(v) => [formatValue(Number(v)), yLabel]} />
              <Line
                type="monotone" dataKey="value"
                stroke="#8b5cf6" strokeWidth={2.5}
                dot={{ r: 3.5, fill: '#7c3aed', strokeWidth: 0 }}
                activeDot={{ r: 5.5, fill: '#c4b5fd', strokeWidth: 0 }}
              />
            </LineChart>
          ) : (
            <BarChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 36 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="name" {...axisProps} tickFormatter={truncateLabel} interval={0}>
                <Label value={xLabel} offset={-16} position="insideBottom" style={{ fill: '#4b5563', fontSize: 11 }} />
              </XAxis>
              <YAxis {...axisProps} tickFormatter={formatValue} width={52}>
                <Label value={yLabel} angle={-90} position="insideLeft" style={{ fill: '#4b5563', fontSize: 11 }} />
              </YAxis>
              <Tooltip {...tooltipStyle} formatter={(v) => [formatValue(Number(v)), yLabel]} />
              <Bar dataKey="value" radius={[5, 5, 0, 0]} maxBarSize={56}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={VIOLET_PALETTE[i % VIOLET_PALETTE.length]} fillOpacity={0.88} />
                ))}
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}
