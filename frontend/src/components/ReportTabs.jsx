import { NavLink, useLocation } from 'react-router-dom'

const TABS = [
  { id: 'pnl', label: 'Consolidated P&L', to: '/pnl' },
  { id: 'balance_sheet', label: 'Balance Sheet', to: '/balance-sheet' },
  { id: 'matrix', label: 'Building-Wise Matrix', to: '/matrix' },
  { id: 'unit', label: 'Unit-Wise P&L', to: '/unit-wise' },
]

export default function ReportTabs() {
  const location = useLocation();

  return (
    <div className="border-b border-slate-800 bg-[#0D1220]">
      <div className="max-w-screen-2xl mx-auto px-6">
        <nav className="flex gap-1" aria-label="Report tabs">
          {TABS.map((tab) => (
            <NavLink
              key={tab.id}
              to={tab.to + location.search}
              className={({ isActive }) =>
                `px-4 py-3 text-xs font-medium tracking-wide transition-all ${
                  isActive ? 'tab-active' : 'tab-inactive'
                }`
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </div>
  )
}
