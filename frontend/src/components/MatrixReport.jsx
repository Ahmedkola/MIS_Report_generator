import { formatCurrency } from '../utils/formatters'

// ─── Row styling config ───────────────────────────────────────────────────────
const ROW_CFG = {
  'Gross Sales':       { color: 'text-slate-200',   bg: '',                   pct: false, bold: false },
  'Net Sales':         { color: 'text-slate-300',   bg: '',                   pct: false, bold: false },
  'Other Income':      { color: 'text-slate-400',   bg: '',                   pct: false, bold: false },
  'Direct Expenses':   { color: 'text-rose-400',    bg: 'bg-rose-950/10',     pct: false, bold: false },
  'Gross Profit':      { color: 'text-emerald-300', bg: 'bg-emerald-950/25',  pct: false, bold: true,  divider: true },
  'Indirect Expenses': { color: 'text-rose-400',    bg: 'bg-rose-950/10',     pct: false, bold: false },
  'EBIDTA':            { color: 'text-gold',        bg: 'bg-amber-950/25',    pct: false, bold: true,  divider: true },
  'EBIDTA %':          { color: 'text-gold-light',  bg: 'bg-amber-950/10',    pct: true,  bold: false },
  'Occupancy %':       { color: 'text-sky-300',     bg: 'bg-sky-950/10',      pct: true,  bold: false },
}

// Rows that are expense rows (display as negative / red regardless of sign)
const EXPENSE_ROWS = new Set(['Direct Expenses', 'Indirect Expenses'])

// ─── Period label: "2026-01" → "Jan 2026" | "2025-04_2026-01" → custom label ─
function periodLabel(period, label) {
  if (label) return label
  if (!period || period.length !== 7) return period
  const [y, m] = period.split('-')
  const date = new Date(Number(y), Number(m) - 1, 1)
  return date.toLocaleDateString('en-IN', { month: 'short', year: '2-digit' }).replace(' ', "-")
}

// ─── Format a single cell value ───────────────────────────────────────────────
function fmtCell(value, isPct) {
  if (value == null || value === 0) return '—'
  if (isPct) return `${value.toFixed(1)}%`
  return formatCurrency(Math.abs(value))
}

// ─── Cell text colour (overrides row colour for sign-sensitive rows) ──────────
function cellColor(value, cfg, rowName) {
  if (cfg.pct) return cfg.color
  if (EXPENSE_ROWS.has(rowName)) return 'text-rose-400'
  if (value < 0) return 'text-rose-400'
  return cfg.color
}

// ─── Single month matrix block ────────────────────────────────────────────────
function MatrixBlock({ matrix, dataCols }) {
  const hasTotalCol = Object.keys(matrix.rows[0]?.cost_centers ?? {}).includes('Total')
  const label = periodLabel(matrix.period, matrix.label)
  const isYTD = matrix.period?.includes('_')

  return (
    <div className="mb-6 last:mb-0">
      {/* Period header bar */}
      <div className={`flex items-center gap-3 px-4 py-2 border-b border-slate-700 ${isYTD ? 'bg-slate-800/80' : 'bg-[#0D1829]'}`}>
        <span className={`text-xs font-semibold tracking-widest uppercase ${isYTD ? 'text-slate-300' : 'text-gold'}`}>
          {label}
        </span>
        {isYTD && (
          <span className="text-[10px] text-slate-500 border border-slate-700 rounded px-1.5 py-0.5">
            Year to Date
          </span>
        )}
      </div>

      {/* Scrollable table */}
      <div className="overflow-x-auto">
        <table className="border-collapse text-xs" style={{ minWidth: `${(dataCols.length + 2) * 108}px` }}>
          <thead>
            <tr className="bg-[#0A0F1E]">
              {/* Sticky row-name header */}
              <th className="sticky left-0 z-20 bg-[#0A0F1E] px-4 py-2.5 text-left font-medium
                             text-slate-500 tracking-widest uppercase whitespace-nowrap
                             border-r border-slate-800 min-w-[160px]">
                Metric
              </th>
              {dataCols.map((col) => (
                <th key={col}
                    className="px-3 py-2.5 text-center font-medium text-slate-500 tracking-wide
                               whitespace-nowrap border-l border-slate-800/50 min-w-[100px]">
                  {col}
                </th>
              ))}
              {hasTotalCol && (
                <th className="px-4 py-2.5 text-center font-semibold text-slate-400 tracking-widest
                               uppercase whitespace-nowrap border-l border-slate-700 bg-[#0A1525] min-w-[110px]">
                  Total
                </th>
              )}
            </tr>
          </thead>

          <tbody>
            {matrix.rows.map((row) => {
              const cfg = ROW_CFG[row.row_name] ?? { color: 'text-slate-300', bg: '', pct: false, bold: false }
              return (
                <tr key={row.row_name}
                    className={`border-t border-slate-800/50 hover:brightness-110 transition-colors
                                ${cfg.bg} ${cfg.divider ? 'border-t-2 border-slate-600' : ''}`}>
                  {/* Sticky metric name */}
                  <td className={`sticky left-0 z-10 px-4 py-2 font-medium whitespace-nowrap
                                  border-r border-slate-800 ${cfg.bg || 'bg-[#0A0F1E]'} ${cfg.color}
                                  ${cfg.bold ? 'font-semibold' : ''}`}>
                    {row.row_name}
                  </td>

                  {dataCols.map((col) => {
                    const val = row.cost_centers?.[col]
                    const isEmpty = val == null || val === 0
                    return (
                      <td key={col}
                          className={`px-3 py-2 text-right font-mono whitespace-nowrap
                                      border-l border-slate-800/30
                                      ${isEmpty ? 'text-slate-700' : cellColor(val, cfg, row.row_name)}
                                      ${cfg.bold ? 'font-semibold' : ''}`}>
                        {fmtCell(val, cfg.pct)}
                      </td>
                    )
                  })}

                  {hasTotalCol && (
                    <td className={`px-4 py-2 text-right font-mono font-semibold whitespace-nowrap
                                    border-l border-slate-700 bg-[#0A1525]
                                    ${cellColor(row.cost_centers?.Total, cfg, row.row_name)}`}>
                      {fmtCell(row.cost_centers?.Total, cfg.pct)}
                    </td>
                  )}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ─── Main export ──────────────────────────────────────────────────────────────
export default function MatrixReport({ matrixList }) {
  if (!matrixList?.length) return (
    <p className="text-slate-500 text-sm px-2">No matrix data available.</p>
  )

  // Collect all data columns (exclude Total) from the first period's first row
  const allCols = Object.keys(matrixList[0]?.rows[0]?.cost_centers ?? {})
  const dataCols = allCols.filter((c) => c !== 'Total')

  return (
    <div className="rounded-xl border border-slate-800 overflow-hidden divide-y divide-slate-800">
      {matrixList.map((matrix, idx) => (
        <MatrixBlock key={matrix.period ?? idx} matrix={matrix} dataCols={dataCols} />
      ))}

      {/* Legend */}
      <div className="flex flex-wrap gap-x-5 gap-y-2 px-4 py-3 bg-[#0D1220]">
        {[
          { label: 'Revenue', cls: 'bg-slate-300' },
          { label: 'Expenses',     cls: 'bg-rose-400' },
          { label: 'Gross Profit', cls: 'bg-emerald-300' },
          { label: 'EBIDTA',       cls: 'bg-amber-400' },
          { label: 'Occupancy',    cls: 'bg-sky-300' },
          { label: 'Negative',     cls: 'bg-rose-500' },
        ].map((l) => (
          <div key={l.label} className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${l.cls}`} />
            <span className="text-[11px] text-slate-500">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
