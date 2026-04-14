import { NavLink, useLocation } from 'react-router-dom'
import { TrendingUp, Scale, Building2, LayoutGrid, ArrowLeftRight, Landmark } from 'lucide-react'

const TABS = [
  { id: 'pnl',          label: 'Consolidated P&L',    to: '/pnl',           icon: TrendingUp },
  { id: 'balance_sheet',label: 'Balance Sheet',        to: '/balance-sheet', icon: Scale },
  { id: 'matrix',       label: 'Building-Wise Matrix', to: '/matrix',        icon: Building2 },
  { id: 'unit',         label: 'Unit-Wise P&L',        to: '/unit-wise',     icon: LayoutGrid },
  { id: 'cash_flow',    label: 'Cash Flow Statement',  to: '/cash-flow',     icon: ArrowLeftRight },
  { id: 'deposits',     label: 'Deposits & Loans',     to: '/deposits-loans',icon: Landmark },
]

export default function ReportTabs() {
  const location = useLocation()

  return (
    <div className="border-b border-slate-800 bg-[#0D1220] sticky top-[65px] z-20 shadow-[0_4px_12px_rgba(0,0,0,0.4)]">
      <div className="max-w-screen-2xl mx-auto px-4 sm:px-6">
        <nav className="flex gap-0.5 overflow-x-auto scrollbar-none" aria-label="Report tabs">
          {TABS.map(({ id, label, to, icon: Icon }) => (
            <NavLink
              key={id}
              to={to + location.search}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-3 py-3 text-xs font-medium tracking-wide whitespace-nowrap transition-all rounded-t-md ${
                  isActive
                    ? 'tab-active bg-gold/10'
                    : 'tab-inactive'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-gold' : ''}`} strokeWidth={isActive ? 2.5 : 1.8} />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
