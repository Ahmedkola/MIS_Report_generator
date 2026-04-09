/**
 * UnitWiseReport.jsx
 * Per-unit P&L matching the Excel "Unit-Wise" sheet.
 *
 * Columns: individual unit cost centers grouped by building.
 * Rows: REVENUE → DIRECT EXPENSES → Gross Profit → INDIRECT EXPENSES → EBITDA → PBT → Metrics
 * Final two columns: Total | Percentage to Revenue
 */

const fmt  = (v) => (v == null || v === 0) ? '-' : Math.round(Math.abs(v)).toLocaleString('en-IN')
const pct  = (v) => (v == null || !isFinite(v) || v === 0) ? '-' : `${Math.round(v)}%`
const fmtSigned = (v) => {
  if (v == null || v === 0) return '-'
  return Math.round(v).toLocaleString('en-IN')
}

// ── Styles ──────────────────────────────────────────────────────────────────
const CELL = 'px-2 py-1 text-right text-[11px] tabular-nums whitespace-nowrap border-r border-slate-800'
const LABEL_CELL = 'pl-2 pr-3 py-1 text-[11px] whitespace-nowrap border-r border-slate-700 sticky left-0 z-10'
const SECTION_HEADER = 'px-2 py-1.5 text-[10px] font-bold tracking-widest uppercase text-slate-400 border-r border-slate-800 bg-[#0D1220]'
const TOTAL_CELL = 'px-2 py-1 text-right text-[11px] tabular-nums font-semibold whitespace-nowrap border-r border-slate-700'
const PCT_CELL   = 'px-2 py-1 text-right text-[11px] tabular-nums text-slate-400 whitespace-nowrap'

const HIGHLIGHT_GREEN = 'bg-emerald-950/60 text-emerald-300 font-semibold'
const HIGHLIGHT_BLUE  = 'bg-blue-950/40 text-blue-300 font-semibold'

// ── Helpers ──────────────────────────────────────────────────────────────────
function buildTotals(activeUnits, data) {
  const tot = {
    gross_sales: 0, gst: 0, host_fees: 0, indirect_income: 0,
    net_sales: 0, net_revenue: 0,
    total_direct_exp: 0, gross_profit: 0,
    total_indirect_exp: 0, ebitda: 0, interest: 0, depreciation: 0, pbt: 0,
    direct_exp: {}, indirect_exp: {},
  }
  for (const disp of activeUnits) {
    const d = data[disp]
    if (!d) continue
    tot.gross_sales       += d.gross_sales      || 0
    tot.gst               += d.gst              || 0
    tot.host_fees         += d.host_fees        || 0
    tot.indirect_income   += d.indirect_income  || 0
    tot.net_sales         += d.net_sales        || 0
    tot.net_revenue       += d.net_revenue      || 0
    tot.total_direct_exp  += d.total_direct_exp || 0
    tot.gross_profit      += d.gross_profit     || 0
    tot.total_indirect_exp += d.total_indirect_exp || 0
    tot.ebitda            += d.ebitda           || 0
    tot.interest          += d.interest         || 0
    tot.depreciation      += d.depreciation     || 0
    tot.pbt               += d.pbt              || 0
    for (const [k, v] of Object.entries(d.direct_exp   || {}))
      tot.direct_exp[k]   = (tot.direct_exp[k]   || 0) + (v || 0)
    for (const [k, v] of Object.entries(d.indirect_exp || {}))
      tot.indirect_exp[k] = (tot.indirect_exp[k] || 0) + (v || 0)
  }
  return tot
}

// ── Building header colspan calculation ─────────────────────────────────────
function buildGroupSpans(activeUnits, columns) {
  const spans = []
  let i = 0
  while (i < activeUnits.length) {
    const bldg = columns.find(([d]) => d === activeUnits[i])?.[1] || ''
    let j = i + 1
    while (j < activeUnits.length && columns.find(([d]) => d === activeUnits[j])?.[1] === bldg)
      j++
    spans.push({ building: bldg, count: j - i })
    i = j
  }
  return spans
}

// ── Main component ────────────────────────────────────────────────────────────
export default function UnitWiseReport({ report }) {
  if (!report?.data || !report?.columns) {
    return (
      <div className="text-slate-500 text-sm py-12 text-center">
        No unit-wise data available.
      </div>
    )
  }

  const { data, columns, direct_rows = [], indirect_rows = [], period } = report

  // Only show columns where there is any meaningful data
  const activeUnits = columns
    .filter(([, bldg]) => bldg !== 'General')   // never show the General Office column
    .map(([d]) => d)
    .filter((disp) => {
      const d = data[disp]
      if (!d) return false
      return (
        (d.gross_sales || 0) !== 0 ||
        (d.total_direct_exp || 0) !== 0 ||
        (d.total_indirect_exp || 0) !== 0
      )
    })

  if (activeUnits.length === 0) {
    return (
      <div className="text-slate-500 text-sm py-12 text-center">
        No unit data for this period.
      </div>
    )
  }

  const totals    = buildTotals(activeUnits, data)
  const groupSpans = buildGroupSpans(activeUnits, columns)

  const getV = (disp, key) => data[disp]?.[key] || 0
  const getTotV = (key) => totals[key] || 0

  const netRevTotal = getTotV('net_revenue')

  // Percentage-to-revenue helper (Total column)
  const revPct = (val) => {
    if (!netRevTotal) return '-'
    return pct((val / netRevTotal) * 100)
  }

  // Cell value for a direct/indirect expense row (always show absolute value)
  const expCell = (disp, row, expKey) => {
    const v = data[disp]?.[expKey]?.[row] || 0
    return v === 0 ? '-' : Math.round(Math.abs(v)).toLocaleString('en-IN')
  }
  const expTot = (row, expKey) => {
    const v = totals[expKey]?.[row] || 0
    return v === 0 ? '-' : Math.round(Math.abs(v)).toLocaleString('en-IN')
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800">
      <table className="border-collapse text-slate-200 bg-[#0A0F1E]" style={{ minWidth: `${(activeUnits.length + 3) * 90}px` }}>
        <thead>
          {/* ── Building group header row ── */}
          <tr className="bg-[#111827]">
            <th className="px-3 py-2 text-left text-[10px] font-semibold text-slate-400 border-r border-slate-700 sticky left-0 z-20 bg-[#111827] min-w-[160px]">
              Particular
            </th>
            {groupSpans.map(({ building, count }) => (
              <th
                key={building}
                colSpan={count}
                className="px-2 py-2 text-center text-[10px] font-semibold text-[#C9A84C] border-r border-slate-700 bg-[#111827]"
              >
                {building}
              </th>
            ))}
            <th className="px-2 py-2 text-center text-[10px] font-semibold text-slate-300 border-r border-slate-700 bg-[#111827]">
              Total
            </th>
            <th className="px-2 py-2 text-center text-[10px] font-semibold text-slate-400 bg-[#111827]">
              % to Revenue
            </th>
          </tr>

          {/* ── Unit sub-header row ── */}
          <tr className="bg-[#0D1220]">
            <th className="px-3 py-1 text-left sticky left-0 z-20 bg-[#0D1220] border-r border-slate-700" />
            {activeUnits.map((disp) => (
              <th key={disp} className="px-2 py-1 text-center text-[10px] text-slate-300 font-medium border-r border-slate-800 whitespace-nowrap">
                {disp}
              </th>
            ))}
            <th className="px-2 py-1 text-center text-[10px] text-slate-300 font-semibold border-r border-slate-700" />
            <th />
          </tr>
        </thead>

        <tbody>
          {/* ══════════════════ REVENUE ══════════════════ */}
          <SectionHeader label="REVENUE" colCount={activeUnits.length} />

          <DataRow label="Gross Sales" labelClass="text-slate-200 font-semibold"
            cells={activeUnits.map((d) => fmt(getV(d, 'gross_sales')))}
            total={fmt(getTotV('gross_sales'))}
            pctCol={revPct(getTotV('gross_sales'))} />

          <DataRow label="  GST" labelClass="text-slate-400"
            cells={activeUnits.map((d) => fmt(getV(d, 'gst')))}
            total={fmt(getTotV('gst'))}
            pctCol="-" />

          <DataRow label="  Host Fees" labelClass="text-slate-400"
            cells={activeUnits.map((d) => fmt(getV(d, 'host_fees')))}
            total={fmt(getTotV('host_fees'))}
            pctCol="-" />

          <DataRow label="Net Sales" labelClass="text-slate-200 font-medium"
            cells={activeUnits.map((d) => fmt(getV(d, 'net_sales')))}
            total={fmt(getTotV('net_sales'))}
            pctCol="-" />

          <DataRow label="  Indirect Income" labelClass="text-violet-300"
            cells={activeUnits.map((d) => fmt(getV(d, 'indirect_income')))}
            total={fmt(getTotV('indirect_income'))}
            pctCol="-" />

          <DataRow label="Net Revenue" labelClass="text-violet-200 font-semibold"
            cells={activeUnits.map((d) => fmt(getV(d, 'net_revenue')))}
            total={fmt(getTotV('net_revenue'))}
            pctCol="-"
            rowClass="border-b border-slate-700" />

          {/* ══════════════════ DIRECT EXPENSES ══════════════════ */}
          <SectionHeader label="DIRECT EXPENSES" colCount={activeUnits.length} />

          {direct_rows.map((row) => (
            <DataRow key={row} label={`  ${row}`} labelClass="text-slate-400"
              cells={activeUnits.map((d) => expCell(d, row, 'direct_exp'))}
              total={expTot(row, 'direct_exp')}
              pctCol={revPct(Math.abs(totals.direct_exp?.[row] || 0))} />
          ))}

          <DataRow label="Total" labelClass="text-rose-300 font-semibold"
            cells={activeUnits.map((d) => fmt(getV(d, 'total_direct_exp')))}
            total={fmt(getTotV('total_direct_exp'))}
            pctCol={revPct(Math.abs(getTotV('total_direct_exp')))}
            rowClass="border-b border-slate-700" />

          {/* ══════════════════ GROSS PROFIT ══════════════════ */}
          <HighlightRow label="Gross Profit" highlight={HIGHLIGHT_GREEN}
            cells={activeUnits.map((d) => fmtSigned(getV(d, 'gross_profit')))}
            total={fmtSigned(getTotV('gross_profit'))}
            pctCol={revPct(getTotV('gross_profit'))} />

          <DataRow label="Gross Profit to Sales %" labelClass="text-slate-400 italic"
            cells={activeUnits.map((d) => {
              const ns = getV(d, 'net_sales')
              const gp = getV(d, 'gross_profit')
              return ns ? pct((gp / ns) * 100) : '-'
            })}
            total={pct(getTotV('net_sales') ? (getTotV('gross_profit') / getTotV('net_sales')) * 100 : 0)}
            pctCol="-"
            rowClass="border-b border-slate-700" />

          {/* ══════════════════ INDIRECT EXPENSES ══════════════════ */}
          <SectionHeader label="INDIRECT EXPENSES" colCount={activeUnits.length} />

          {indirect_rows.map((row) => (
            <DataRow key={row} label={`  ${row}`} labelClass="text-slate-400"
              cells={activeUnits.map((d) => expCell(d, row, 'indirect_exp'))}
              total={expTot(row, 'indirect_exp')}
              pctCol={revPct(Math.abs(totals.indirect_exp?.[row] || 0))} />
          ))}

          <DataRow label="Total" labelClass="text-rose-300 font-semibold"
            cells={activeUnits.map((d) => fmt(getV(d, 'total_indirect_exp')))}
            total={fmt(getTotV('total_indirect_exp'))}
            pctCol={revPct(Math.abs(getTotV('total_indirect_exp')))}
            rowClass="border-b border-slate-700" />

          {/* ══════════════════ EBITDA ══════════════════ */}
          <HighlightRow label="EBITDA" highlight={HIGHLIGHT_GREEN}
            cells={activeUnits.map((d) => fmtSigned(getV(d, 'ebitda')))}
            total={fmtSigned(getTotV('ebitda'))}
            pctCol={revPct(getTotV('ebitda'))} />

          <DataRow label="EBITDA to Sales %" labelClass="text-slate-400 italic"
            cells={activeUnits.map((d) => {
              const ns = getV(d, 'net_sales')
              const eb = getV(d, 'ebitda')
              return ns ? pct((eb / ns) * 100) : '-'
            })}
            total={pct(getTotV('net_sales') ? (getTotV('ebitda') / getTotV('net_sales')) * 100 : 0)}
            pctCol="-" />

          <DataRow label="  Interest" labelClass="text-slate-400"
            cells={activeUnits.map(() => '-')}
            total="-" pctCol="-" />

          <DataRow label="  Depreciation" labelClass="text-slate-400"
            cells={activeUnits.map(() => '-')}
            total="-" pctCol="-" />

          {/* ══════════════════ PROFIT BEFORE TAX ══════════════════ */}
          <HighlightRow label="Profit Before Tax" highlight={HIGHLIGHT_GREEN}
            cells={activeUnits.map((d) => fmtSigned(getV(d, 'pbt')))}
            total={fmtSigned(getTotV('pbt'))}
            pctCol={revPct(getTotV('pbt'))} />

          <DataRow label="PBT %" labelClass="text-slate-400 italic"
            cells={activeUnits.map((d) => {
              const ns = getV(d, 'net_sales')
              const pb = getV(d, 'pbt')
              return ns ? pct((pb / ns) * 100) : '-'
            })}
            total={pct(getTotV('net_sales') ? (getTotV('pbt') / getTotV('net_sales')) * 100 : 0)}
            pctCol="-"
            rowClass="border-b border-slate-700" />

          {/* ══════════════════ METRICS ══════════════════ */}
          <SectionHeader label="METRICS" colCount={activeUnits.length} />

          <DataRow label="No of Days Stay" labelClass="text-slate-400"
            cells={activeUnits.map(() => '-')}
            total="-" pctCol="-" />

          <DataRow label="Available Room Days" labelClass="text-slate-400"
            cells={activeUnits.map(() => '-')}
            total="-" pctCol="-" />

          <DataRow label="Occupancy %" labelClass="text-slate-400"
            cells={activeUnits.map(() => '-')}
            total="-" pctCol="-" />

          <DataRow label="Average Rent Per Day" labelClass="text-slate-400"
            cells={activeUnits.map((d) => {
              const ns = getV(d, 'net_sales')
              return ns ? Math.round(ns / 30).toLocaleString('en-IN') : '-'
            })}
            total={getTotV('net_sales') ? Math.round(getTotV('net_sales') / 30).toLocaleString('en-IN') : '-'}
            pctCol="-" />
        </tbody>
      </table>
    </div>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionHeader({ label, colCount }) {
  return (
    <tr className="bg-[#0D1220]">
      <td className={`${LABEL_CELL} ${SECTION_HEADER} bg-[#0D1220]`}>{label}</td>
      {Array.from({ length: colCount }).map((_, i) => (
        <td key={i} className={SECTION_HEADER}></td>
      ))}
      <td className={SECTION_HEADER}></td>
      <td className={SECTION_HEADER}></td>
    </tr>
  )
}

function DataRow({ label, labelClass = '', cells, total, pctCol, rowClass = '' }) {
  return (
    <tr className={`hover:bg-slate-800/20 border-b border-slate-800/40 ${rowClass}`}>
      <td className={`${LABEL_CELL} bg-[#0A0F1E] ${labelClass}`}>{label}</td>
      {cells.map((val, i) => (
        <td key={i} className={CELL}>{val}</td>
      ))}
      <td className={TOTAL_CELL}>{total}</td>
      <td className={PCT_CELL}>{pctCol}</td>
    </tr>
  )
}

function HighlightRow({ label, highlight, cells, total, pctCol }) {
  return (
    <tr className={`${highlight} border-y border-emerald-900/40`}>
      <td className={`${LABEL_CELL} ${highlight}`}>{label}</td>
      {cells.map((val, i) => (
        <td key={i} className={`${CELL} ${highlight}`}>{val}</td>
      ))}
      <td className={`${TOTAL_CELL} ${highlight}`}>{total}</td>
      <td className={`${PCT_CELL} ${highlight}`}>{pctCol}</td>
    </tr>
  )
}
