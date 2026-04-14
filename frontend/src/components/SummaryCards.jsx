import { DollarSign, TrendingUp, TrendingDown, BarChart3, Users } from 'lucide-react'
import { formatCurrency } from '../utils/formatters'

function Card({ label, value, sub, positive, icon: Icon, accentClass }) {
  const col = positive == null ? 'text-gold' : positive ? 'text-emerald-400' : 'text-rose-400'
  const iconCol = positive == null ? 'text-gold/40' : positive ? 'text-emerald-400/40' : 'text-rose-400/40'
  return (
    <div className={`bg-[#111827] border border-slate-800 rounded-xl px-5 py-4 relative overflow-hidden card-hover ${accentClass}`}>
      {Icon && (
        <Icon className={`absolute top-3 right-3 w-5 h-5 ${iconCol}`} strokeWidth={1.5} />
      )}
      <p className="text-xs text-slate-500 tracking-widest uppercase mb-2">{label}</p>
      <p className={`text-xl font-bold font-mono ${col}`}>{value}</p>
      {sub && <p className="text-xs text-slate-600 mt-1">{sub}</p>}
    </div>
  )
}

export default function SummaryCards({ pnl, matrix }) {
  if (!pnl) return null
  const { summary } = pnl
  const ebidtaPct = matrix?.[0]?.rows?.find((r) => r.row_name === 'EBIDTA %')
  const occupancy = matrix?.[0]?.rows?.find((r) => r.row_name === 'Occupancy %')
  const isProfit = summary?.net_profit >= 0

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      <Card
        label="Total Revenue"
        value={formatCurrency(summary?.total_income)}
        positive={true}
        icon={DollarSign}
        accentClass="border-l-4 border-l-emerald-500"
      />
      <Card
        label="Net Profit"
        value={formatCurrency(Math.abs(summary?.net_profit))}
        positive={isProfit}
        sub={isProfit ? 'Profit' : 'Loss'}
        icon={isProfit ? TrendingUp : TrendingDown}
        accentClass={isProfit ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-rose-500'}
      />
      {ebidtaPct && (
        <Card
          label="EBIDTA Margin"
          value={`${ebidtaPct.cost_centers?.Total?.toFixed(1) ?? '—'}%`}
          positive={null}
          icon={BarChart3}
          accentClass="border-l-4 border-l-gold"
        />
      )}
      {occupancy && (
        <Card
          label="Avg Occupancy"
          value={`${occupancy.cost_centers?.Total?.toFixed(1) ?? '—'}%`}
          positive={null}
          icon={Users}
          accentClass="border-l-4 border-l-sky-500"
        />
      )}
    </div>
  )
}
