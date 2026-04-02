import { formatCurrency } from '../utils/formatters'

function Card({ label, value, sub, positive }) {
  const col = positive == null ? 'text-gold' : positive ? 'text-emerald-400' : 'text-rose-400'
  return (
    <div className="bg-[#111827] border border-slate-800 rounded-xl px-5 py-4">
      <p className="text-xs text-slate-500 tracking-widest uppercase mb-2">{label}</p>
      <p className={`text-xl font-bold font-mono ${col}`}>{value}</p>
      {sub && <p className="text-xs text-slate-600 mt-1">{sub}</p>}
    </div>
  )
}

export default function SummaryCards({ pnl, matrix }) {
  if (!pnl) return null
  const { summary } = pnl
  const totalRow = matrix?.[0]?.rows?.find((r) => r.row_name === 'EBIDTA')
  const ebidtaPct = matrix?.[0]?.rows?.find((r) => r.row_name === 'EBIDTA %')
  const occupancy = matrix?.[0]?.rows?.find((r) => r.row_name === 'Occupancy %')

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <Card
        label="Total Revenue"
        value={formatCurrency(summary?.total_income)}
        positive={true}
      />
      <Card
        label="Net Profit"
        value={formatCurrency(Math.abs(summary?.net_profit))}
        positive={summary?.net_profit >= 0}
        sub={summary?.net_profit >= 0 ? 'Profit' : 'Loss'}
      />
      {ebidtaPct && (
        <Card
          label="EBIDTA Margin"
          value={`${ebidtaPct.cost_centers?.Total?.toFixed(1) ?? '—'}%`}
          positive={null}
        />
      )}
      {occupancy && (
        <Card
          label="Avg Occupancy"
          value={`${occupancy.cost_centers?.Total?.toFixed(1) ?? '—'}%`}
          positive={null}
        />
      )}
    </div>
  )
}
