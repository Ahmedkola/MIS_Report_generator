import { useReport } from '../context/ReportContext'
import { formatCurrency, formatPeriod } from '../utils/formatters'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'

function LedgerTable({ title, rows, total, accentColor, emptyMsg }) {
  return (
    <div className="rounded-xl border border-slate-800 overflow-hidden">
      <div className="bg-[#0D1220] px-5 py-3 border-b border-slate-800 flex items-center justify-between">
        <p className="text-xs font-bold tracking-widest uppercase" style={{ color: accentColor }}>
          {title}
        </p>
        <p className="font-mono font-bold text-sm" style={{ color: accentColor }}>
          {formatCurrency(total)}
        </p>
      </div>

      {rows.length === 0 ? (
        <div className="px-5 py-8 text-center text-xs text-slate-600">{emptyMsg}</div>
      ) : (
        <table className="w-full border-collapse">
          <thead>
            <tr className="bg-[#0A0F1E] border-b border-slate-700">
              <th className="px-4 py-2.5 text-left text-[10px] font-semibold text-slate-500 tracking-widest uppercase">
                Particulars
              </th>
              <th className="px-4 py-2.5 text-right text-[10px] font-semibold text-slate-500 tracking-widest uppercase">
                Amount (₹)
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.name} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                <td className="px-4 py-2.5 text-xs text-slate-300">{r.name}</td>
                <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-200 whitespace-nowrap">
                  {formatCurrency(r.amount)}
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="bg-[#0D1829] border-t-2 border-slate-600">
              <td className="px-4 py-2.5 text-xs font-bold text-slate-200">Total</td>
              <td
                className="px-4 py-2.5 text-right font-mono text-xs font-bold whitespace-nowrap"
                style={{ color: accentColor }}
              >
                {formatCurrency(total)}
              </td>
            </tr>
          </tfoot>
        </table>
      )}
    </div>
  )
}

export default function DepositsLoansPage() {
  const { data, loading, error } = useReport()

  if (loading) return <LoadingState />
  if (error)   return <ErrorState error={error} />
  if (!data)   return <EmptyState />

  const dl = data.deposits_loans
  if (!dl)     return <EmptyState />

  const { deposits, loans, total_deposits, total_loans, period } = dl

  return (
    <section>
      <SectionTitle
        title="Security Deposits & Loans"
        sub={formatPeriod(period)}
      />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <LedgerTable
          title="Security Deposits"
          rows={deposits}
          total={total_deposits}
          accentColor="#34d399"
          emptyMsg="No security deposit ledgers found for this period"
        />
        <LedgerTable
          title="Loans (Liabilities)"
          rows={loans}
          total={total_loans}
          accentColor="#f87171"
          emptyMsg="No loan ledgers found for this period"
        />
      </div>

      {/* Summary footer */}
      <div className="mt-4 flex flex-wrap gap-6 px-5 py-3 rounded-xl border border-slate-800 bg-[#0D1220]">
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">Total Security Deposits</p>
          <p className="font-mono font-bold text-sm text-emerald-300">{formatCurrency(total_deposits)}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">Total Loans</p>
          <p className="font-mono font-bold text-sm text-rose-400">{formatCurrency(total_loans)}</p>
        </div>
        <div>
          <p className="text-[10px] text-slate-500 tracking-widest uppercase mb-0.5">Net (Deposits − Loans)</p>
          <p className={`font-mono font-bold text-sm ${total_deposits - total_loans >= 0 ? 'text-emerald-300' : 'text-rose-400'}`}>
            {formatCurrency(Math.abs(total_deposits - total_loans))}
          </p>
        </div>
      </div>
    </section>
  )
}
