import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip,
  Label,
} from 'recharts'

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

function chartTitle(xKey: string, yKey: string): string {
  const fmt = (s: string) => s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  return `${fmt(yKey)} by ${fmt(xKey)}`
}

const tooltipStyle = {
  contentStyle: {
    background: '#161616',
    border: '0.5px solid rgba(255,255,255,0.1)',
    borderRadius: '6px',
    fontSize: '12px',
    color: 'rgba(255,255,255,0.75)',
    boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
  },
  labelStyle: { color: 'rgba(255,255,255,0.45)', fontWeight: 500, marginBottom: 2 },
  cursor: { fill: 'rgba(255,255,255,0.04)' },
}

const axisProps = {
  stroke: 'transparent',
  tick: { fill: 'rgba(255,255,255,0.2)', fontSize: 11 },
  tickLine: false,
  axisLine: false,
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

  return (
    <div style={{
      background: 'rgba(255,255,255,0.02)',
      border: '0.5px solid rgba(255,255,255,0.08)',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '0.5px solid rgba(255,255,255,0.06)',
      }}>
        <span style={{ fontSize: '13px', color: 'rgba(255,255,255,0.6)', fontWeight: 500 }}>{title}</span>
        <span style={{
          fontSize: '10px',
          color: 'rgba(255,255,255,0.25)',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
        }}>
          {cfg.type === 'line' ? 'trend' : 'bar chart'}
        </span>
      </div>

      {/* Chart */}
      <div style={{ padding: '16px 8px 12px' }}>
        <ResponsiveContainer width="100%" height={280}>
          {cfg.type === 'line' ? (
            <LineChart data={chartData} margin={{ top: 8, right: 20, left: 8, bottom: 36 }}>
              <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis dataKey="name" {...axisProps} tickFormatter={truncateLabel} interval="preserveStartEnd">
                <Label value={xLabel} offset={-16} position="insideBottom" style={{ fill: 'rgba(255,255,255,0.18)', fontSize: 11 }} />
              </XAxis>
              <YAxis {...axisProps} tickFormatter={formatValue} width={52}>
                <Label value={yLabel} angle={-90} position="insideLeft" style={{ fill: 'rgba(255,255,255,0.18)', fontSize: 11 }} />
              </YAxis>
              <Tooltip {...tooltipStyle} formatter={(v) => [formatValue(Number(v)), yLabel]} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="rgba(255,255,255,0.5)"
                strokeWidth={1.5}
                dot={{ r: 3, fill: 'rgba(255,255,255,0.4)', strokeWidth: 0 }}
                activeDot={{ r: 4.5, fill: 'rgba(255,255,255,0.8)', strokeWidth: 0 }}
              />
            </LineChart>
          ) : (
            <BarChart data={chartData} margin={{ top: 8, right: 20, left: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="2 4" stroke="rgba(255,255,255,0.04)" vertical={false} />
              <XAxis
                dataKey="name"
                {...axisProps}
                tick={{ fill: 'rgba(255,255,255,0.2)', fontSize: 11 }}
                tickFormatter={truncateLabel}
                interval={0}
                angle={-45}
                textAnchor="end"
                height={70}
              />
              <YAxis {...axisProps} tickFormatter={formatValue} width={52}>
                <Label value={yLabel} angle={-90} position="insideLeft" style={{ fill: 'rgba(255,255,255,0.18)', fontSize: 11 }} />
              </YAxis>
              <Tooltip {...tooltipStyle} formatter={(v) => [formatValue(Number(v)), yLabel]} />
              <Bar
                dataKey="value"
                fill="rgba(255,255,255,0.15)"
                activeBar={{ fill: 'rgba(255,255,255,0.3)' }}
                radius={[3, 3, 0, 0]}
                maxBarSize={52}
              />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}
