import { formatCurrency } from '../utils/formatters'

// ─── Which groups belong to which section of the T-account ───────────────────
// Trading Dr  = Direct Expenses
// Trading Cr  = Sales Accounts, Direct Incomes (any non-Indirect income group)
// P&L Dr      = Indirect Expenses
// P&L Cr      = Indirect Incomes
const INDIRECT_INCOME_GROUPS = new Set(['Indirect Incomes', 'Indirect Income'])

function fmt(v) {
  return v != null ? formatCurrency(Math.abs(v)) : '—'
}

// ─── Single item row within a column ─────────────────────────────────────────
function ItemRow({ name, amount, indent = false, color = 'text-slate-400' }) {
  return (
    <tr>
      <td className={`py-0.5 text-xs ${indent ? 'pl-8 pr-2' : 'px-3'} ${color} truncate max-w-[200px]`}>
        {name}
      </td>
      <td className={`py-0.5 px-3 text-right font-mono text-xs whitespace-nowrap ${color}`}>
        {amount != null ? fmt(amount) : ''}
      </td>
    </tr>
  )
}

// ─── Group block: header + items + subtotal ───────────────────────────────────
function GroupBlock({ group, itemColor, subtotalColor, showSubtotal = true }) {
  const items = Object.values(group.items ?? {})
  return (
    <>
      <tr>
        <td colSpan={2} className="px-3 pt-3 pb-0.5 text-xs font-bold text-slate-200 tracking-wide">
          {group.group_name}
        </td>
      </tr>
      {items.map((item) => (
        <ItemRow key={item.name} name={item.name} amount={item.amount} indent color={itemColor} />
      ))}
      {showSubtotal && (
        <tr className="border-t border-slate-700/50">
          <td className="px-3 py-1 text-xs font-semibold text-slate-300 italic">
            {/* spacer */}
          </td>
          <td className={`px-3 py-1 text-right font-mono text-xs font-bold whitespace-nowrap ${subtotalColor}`}>
            {fmt(group.subtotal)}
          </td>
        </tr>
      )}
    </>
  )
}

// ─── Divider row spanning the outer table ────────────────────────────────────
function TotalDividerRow({ leftLabel, leftVal, rightLabel, rightVal, labelColor = 'text-slate-200' }) {
  return (
    <tr className="border-t-2 border-slate-600 bg-[#0D1829]">
      <td className={`px-3 py-2 text-xs font-bold tracking-wide ${labelColor}`}>{leftLabel}</td>
      <td className={`px-3 py-2 text-right font-mono text-xs font-bold whitespace-nowrap ${labelColor}`}>
        {leftVal != null ? fmt(leftVal) : ''}
      </td>
      <td className="w-px bg-slate-700" />
      <td className={`px-3 py-2 text-xs font-bold tracking-wide ${labelColor}`}>{rightLabel}</td>
      <td className={`px-3 py-2 text-right font-mono text-xs font-bold whitespace-nowrap ${labelColor}`}>
        {rightVal != null ? fmt(rightVal) : ''}
      </td>
    </tr>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────
export default function PnLReport({ report }) {
  if (!report) return null

  const { sections, summary } = report
  const incomeGroups = sections?.Income ?? {}

  // API returns Direct Expenses under sections['Direct Expenses'] (top-level key)
  // and Indirect Expenses under sections['Expenses']
  const directExpSection   = sections?.['Direct Expenses'] ?? {}
  const indirectExpSection = sections?.Expenses ?? {}

  // Partition income groups
  const salesGroups = Object.values(incomeGroups).filter(
    (g) => !INDIRECT_INCOME_GROUPS.has(g.group_name)
  )
  const indirectIncomeGroups = Object.values(incomeGroups).filter(
    (g) => INDIRECT_INCOME_GROUPS.has(g.group_name)
  )

  // All groups in their respective sections
  const directExpGroups   = Object.values(directExpSection)
  const indirectExpGroups = Object.values(indirectExpSection)

  // Compute totals
  const totalSales       = salesGroups.reduce((s, g) => s + Math.abs(g.subtotal ?? 0), 0)
  const totalDirectExp   = directExpGroups.reduce((s, g) => s + Math.abs(g.subtotal ?? 0), 0)
  const grossProfit      = totalSales - totalDirectExp
  // Trading total = Sales + Direct Incomes (Cr side) = Direct Exp + Gross Profit (Dr side)
  const tradingTotal     = totalSales

  const totalIndirectInc = indirectIncomeGroups.reduce((s, g) => s + Math.abs(g.subtotal ?? 0), 0)
  const totalIndirectExp = indirectExpGroups.reduce((s, g) => s + Math.abs(g.subtotal ?? 0), 0)
  const netProfit        = grossProfit + totalIndirectInc - totalIndirectExp
  const plTotal          = grossProfit + totalIndirectInc   // = indirectExp + netProfit
  const isProfit         = netProfit >= 0

  // Use summary if available (backend-computed is more accurate)
  const summaryNetProfit = summary?.net_profit
  const displayNetProfit = summaryNetProfit != null ? summaryNetProfit : netProfit

  return (
    <div className="rounded-xl border border-slate-800 overflow-hidden">
      {/* Company / period header */}
      <div className="bg-[#0D1220] px-5 py-3 border-b border-slate-800">
        <p className="text-xs font-bold text-slate-300 tracking-widest uppercase">
          {report.company}
        </p>
        <p className="text-[11px] text-slate-500 mt-0.5">
          Profit &amp; Loss Account &nbsp;·&nbsp; {report.period}
        </p>
      </div>

      {/* Two-column T-account table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse min-w-[700px]">
          {/* Column headers */}
          <thead>
            <tr className="bg-[#0A0F1E] border-b border-slate-700">
              <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-slate-500 tracking-widest uppercase w-[35%]">
                Dr — Particulars
              </th>
              <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-slate-500 tracking-widest uppercase w-[15%]">
                Amount (₹)
              </th>
              {/* Vertical divider */}
              <th className="w-px bg-slate-700 p-0" />
              <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-slate-500 tracking-widest uppercase w-[35%]">
                Cr — Particulars
              </th>
              <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-slate-500 tracking-widest uppercase w-[15%]">
                Amount (₹)
              </th>
            </tr>
          </thead>

          <tbody>
            {/* ── TRADING SECTION ─────────────────────────────────────────── */}
            <tr className="bg-slate-800/30">
              <td colSpan={2} className="px-3 py-1.5 text-[10px] font-bold text-slate-500 tracking-[0.2em] uppercase">
                Trading Account
              </td>
              <td className="w-px bg-slate-700" />
              <td colSpan={2} className="px-3 py-1.5 text-[10px] font-bold text-slate-500 tracking-[0.2em] uppercase">
                &nbsp;
              </td>
            </tr>

            {/* Trading Dr: Direct Expenses | Trading Cr: Sales */}
            <tr className="align-top">
              {/* LEFT: Direct Expenses */}
              <td colSpan={2} className="border-r border-slate-800 align-top p-0">
                <table className="w-full">
                  {directExpGroups.map((g) => (
                    <GroupBlock
                      key={g.group_name}
                      group={g}
                      itemColor="text-slate-400"
                      subtotalColor="text-rose-300"
                    />
                  ))}
                  {/* Gross Profit c/o */}
                  {grossProfit > 0 && (
                    <tr className="border-t border-slate-700/50">
                      <td className="px-3 py-1.5 text-xs font-bold text-emerald-300">
                        Gross Profit c/o
                      </td>
                      <td className="px-3 py-1.5 text-right font-mono text-xs font-bold text-emerald-300 whitespace-nowrap">
                        {fmt(grossProfit)}
                      </td>
                    </tr>
                  )}
                </table>
              </td>

              <td className="w-px bg-slate-700 p-0" />

              {/* RIGHT: Sales + Direct Incomes */}
              <td colSpan={2} className="align-top p-0">
                <table className="w-full">
                  {salesGroups.map((g) => (
                    <GroupBlock
                      key={g.group_name}
                      group={g}
                      itemColor="text-slate-400"
                      subtotalColor="text-emerald-300"
                    />
                  ))}
                </table>
              </td>
            </tr>

            {/* Trading totals row */}
            <TotalDividerRow
              leftLabel="Total"
              leftVal={tradingTotal}
              rightLabel="Total"
              rightVal={tradingTotal}
              labelColor="text-slate-300"
            />

            {/* ── P&L SECTION ─────────────────────────────────────────────── */}
            <tr className="bg-slate-800/30">
              <td colSpan={2} className="px-3 py-1.5 text-[10px] font-bold text-slate-500 tracking-[0.2em] uppercase">
                Profit &amp; Loss Account
              </td>
              <td className="w-px bg-slate-700" />
              <td colSpan={2} className="px-3 py-1.5 text-[10px] font-bold text-slate-500 tracking-[0.2em] uppercase">
                &nbsp;
              </td>
            </tr>

            {/* P&L Dr: Indirect Expenses | P&L Cr: Gross Profit b/f + Indirect Incomes */}
            <tr className="align-top">
              {/* LEFT: Indirect Expenses + Net Profit */}
              <td colSpan={2} className="border-r border-slate-800 align-top p-0">
                <table className="w-full">
                  {indirectExpGroups.map((g) => (
                    <GroupBlock
                      key={g.group_name}
                      group={g}
                      itemColor="text-slate-400"
                      subtotalColor="text-rose-300"
                    />
                  ))}
                  {/* Net Profit / Loss */}
                  <tr className="border-t border-slate-700/50">
                    <td className={`px-3 py-1.5 text-xs font-bold ${isProfit ? 'text-emerald-300' : 'text-rose-300'}`}>
                      {isProfit ? 'Nett Profit' : 'Nett Loss'}
                    </td>
                    <td className={`px-3 py-1.5 text-right font-mono text-xs font-bold whitespace-nowrap ${isProfit ? 'text-emerald-300' : 'text-rose-300'}`}>
                      {fmt(displayNetProfit)}
                    </td>
                  </tr>
                </table>
              </td>

              <td className="w-px bg-slate-700 p-0" />

              {/* RIGHT: Gross Profit b/f + Indirect Incomes */}
              <td colSpan={2} className="align-top p-0">
                <table className="w-full">
                  {/* Gross Profit b/f */}
                  <tr>
                    <td className="px-3 pt-3 pb-0.5 text-xs font-bold text-emerald-300">
                      Gross Profit b/f
                    </td>
                    <td className="px-3 pt-3 pb-0.5 text-right font-mono text-xs font-bold text-emerald-300 whitespace-nowrap">
                      {fmt(grossProfit)}
                    </td>
                  </tr>
                  {indirectIncomeGroups.map((g) => (
                    <GroupBlock
                      key={g.group_name}
                      group={g}
                      itemColor="text-slate-400"
                      subtotalColor="text-emerald-300"
                    />
                  ))}
                </table>
              </td>
            </tr>

            {/* P&L totals row */}
            <TotalDividerRow
              leftLabel="Total"
              leftVal={plTotal}
              rightLabel="Total"
              rightVal={plTotal}
              labelColor="text-slate-300"
            />
          </tbody>
        </table>
      </div>

      {/* Summary footer */}
      <div className="flex flex-wrap gap-6 px-5 py-3 border-t border-slate-700 bg-[#0D1220]">
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">Gross Profit</p>
          <p className="font-mono font-bold text-sm text-emerald-300">{fmt(grossProfit)}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">
            {isProfit ? 'Net Profit' : 'Net Loss'}
          </p>
          <p className={`font-mono font-bold text-sm ${isProfit ? 'text-emerald-300' : 'text-rose-300'}`}>
            {fmt(displayNetProfit)}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">Total Revenue</p>
          <p className="font-mono font-bold text-sm text-slate-200">{fmt(tradingTotal)}</p>
        </div>
      </div>
    </div>
  )
}
