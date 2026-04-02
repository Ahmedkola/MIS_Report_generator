import { formatCurrency } from '../utils/formatters'

function fmt(v) {
  return v != null ? formatCurrency(Math.abs(v)) : '—'
}

// Single line item row
function ItemRow({ name, amount, color = 'text-slate-400' }) {
  return (
    <tr>
      <td className={`py-0.5 pl-8 pr-2 text-xs ${color} truncate max-w-[200px]`}>{name}</td>
      <td className={`py-0.5 px-3 text-right font-mono text-xs whitespace-nowrap ${color}`}>
        {fmt(amount)}
      </td>
    </tr>
  )
}

// Group block: bold name + amount on same row (BS groups are single values from Tally)
function GroupBlock({ group, subtotalColor = 'text-slate-300' }) {
  const items = Object.values(group.items ?? {})
  // If there's only one item with the same name as the group, show as a single row
  const isSingleSelf = items.length === 1 && items[0].name === group.group_name
  return (
    <>
      {isSingleSelf ? (
        <tr>
          <td className="px-3 pt-3 pb-1.5 text-xs font-bold text-slate-200 tracking-wide">{group.group_name}</td>
          <td className={`px-3 pt-3 pb-1.5 text-right font-mono text-xs font-bold whitespace-nowrap ${subtotalColor}`}>
            {fmt(group.subtotal)}
          </td>
        </tr>
      ) : (
        <>
          <tr>
            <td colSpan={2} className="px-3 pt-3 pb-0.5 text-xs font-bold text-slate-200 tracking-wide">
              {group.group_name}
            </td>
          </tr>
          {items.map((item) => (
            <ItemRow key={item.name} name={item.name} amount={item.amount} />
          ))}
          <tr className="border-t border-slate-700/50">
            <td className="px-3 py-1 text-xs text-slate-500 italic">Total {group.group_name}</td>
            <td className={`px-3 py-1 text-right font-mono text-xs font-bold whitespace-nowrap ${subtotalColor}`}>
              {fmt(group.subtotal)}
            </td>
          </tr>
        </>
      )}
    </>
  )
}

export default function BalanceSheet({ report }) {
  if (!report) return null

  const { sections } = report
  const assetSection  = sections?.Assets ?? {}
  const liabSection   = sections?.['Equity & Liabilities'] ?? {}

  // Section-level totals (assets are Dr = negative, take abs)
  const totalAssets = Object.values(assetSection).reduce((s, g) => s + Math.abs(g.subtotal ?? 0), 0)
  const totalLiab   = Object.values(liabSection).reduce((s, g) => s + Math.abs(g.subtotal ?? 0), 0)

  // Canonical order for each side
  const LIAB_ORDER = ['Capital Account', 'Loans (Liability)', 'Current Liabilities']
  const ASSET_ORDER = ['Fixed Assets', 'Current Assets']

  function orderedGroups(section, order) {
    const known = order.flatMap((name) => {
      const g = Object.values(section).find((x) => x.group_name === name)
      return g ? [g] : []
    })
    const rest = Object.values(section).filter(
      (g) => !order.includes(g.group_name)
    )
    return [...known, ...rest]
  }

  const liabGroups  = orderedGroups(liabSection, LIAB_ORDER)
  const assetGroups = orderedGroups(assetSection, ASSET_ORDER)

  return (
    <div className="rounded-xl border border-slate-800 overflow-hidden">
      {/* Header */}
      <div className="bg-[#0D1220] px-5 py-3 border-b border-slate-800">
        <p className="text-xs font-bold text-slate-300 tracking-widest uppercase">
          {report.company}
        </p>
        <p className="text-[11px] text-slate-500 mt-0.5">
          Balance Sheet &nbsp;·&nbsp; {report.period}
        </p>
      </div>

      {/* Two-column T-account */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse min-w-[700px]">
          <thead>
            <tr className="bg-[#0A0F1E] border-b border-slate-700">
              <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-slate-500 tracking-widest uppercase w-[35%]">
                Liabilities &amp; Capital
              </th>
              <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-slate-500 tracking-widest uppercase w-[15%]">
                Amount (₹)
              </th>
              {/* vertical divider */}
              <th className="w-px bg-slate-700 p-0" />
              <th className="px-3 py-2.5 text-left text-[10px] font-semibold text-slate-500 tracking-widest uppercase w-[35%]">
                Assets
              </th>
              <th className="px-3 py-2.5 text-right text-[10px] font-semibold text-slate-500 tracking-widest uppercase w-[15%]">
                Amount (₹)
              </th>
            </tr>
          </thead>

          <tbody>
            <tr className="align-top">
              {/* LEFT — Liabilities */}
              <td colSpan={2} className="border-r border-slate-800 align-top p-0">
                <table className="w-full">
                  {liabGroups.map((g) => (
                    <GroupBlock key={g.group_name} group={g} subtotalColor="text-violet-300" />
                  ))}
                </table>
              </td>

              <td className="w-px bg-slate-700 p-0" />

              {/* RIGHT — Assets */}
              <td colSpan={2} className="align-top p-0">
                <table className="w-full">
                  {assetGroups.map((g) => (
                    <GroupBlock key={g.group_name} group={g} subtotalColor="text-sky-300" />
                  ))}
                </table>
              </td>
            </tr>

            {/* Grand Total row */}
            <tr className="border-t-2 border-slate-600 bg-[#0D1829]">
              <td className="px-3 py-2 text-xs font-bold text-slate-200 tracking-wide">Total</td>
              <td className="px-3 py-2 text-right font-mono text-xs font-bold text-slate-200 whitespace-nowrap">
                {fmt(totalLiab)}
              </td>
              <td className="w-px bg-slate-700" />
              <td className="px-3 py-2 text-xs font-bold text-slate-200 tracking-wide">Total</td>
              <td className="px-3 py-2 text-right font-mono text-xs font-bold text-slate-200 whitespace-nowrap">
                {fmt(totalAssets)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Summary footer */}
      <div className="flex flex-wrap gap-6 px-5 py-3 border-t border-slate-700 bg-[#0D1220]">
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">Total Liabilities</p>
          <p className="font-mono font-bold text-sm text-violet-300">{fmt(totalLiab)}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">Total Assets</p>
          <p className="font-mono font-bold text-sm text-sky-300">{fmt(totalAssets)}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">Difference</p>
          <p className={`font-mono font-bold text-sm ${Math.abs(totalAssets - totalLiab) < 10 ? 'text-emerald-300' : 'text-rose-400'}`}>
            {fmt(totalAssets - totalLiab)}
          </p>
        </div>
      </div>
    </div>
  )
}
