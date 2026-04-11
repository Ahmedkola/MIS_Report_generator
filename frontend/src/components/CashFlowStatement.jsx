import { useState } from 'react'
import { fetchCashFlow } from '../utils/api'

// ── Formatting helpers ─────────────────────────────────────────────────────

function fmtIndian(value) {
  if (value === null || value === undefined || isNaN(value)) return '—'
  const abs = Math.abs(Math.round(value))
  const neg = value < 0
  // Indian number format: last 3 digits, then groups of 2
  const s = abs.toString()
  let result = ''
  if (s.length <= 3) {
    result = s
  } else {
    result = s.slice(-3)
    let rem = s.slice(0, -3)
    while (rem.length > 2) {
      result = rem.slice(-2) + ',' + result
      rem = rem.slice(0, -2)
    }
    result = rem + ',' + result
  }
  return neg ? `(${result})` : result
}

function isZero(v) {
  return !v || Math.abs(v) < 0.5
}

// ── Row types ─────────────────────────────────────────────────────────────

function SectionHeader({ label }) {
  return (
    <tr className="border-t-2 border-slate-600">
      <td colSpan={3} className="py-2 px-4 font-bold text-slate-100 text-sm bg-slate-800/60">
        {label}
      </td>
    </tr>
  )
}

function DataRow({ label, p1, p2, indent = false, dimZero = true }) {
  const z1 = isZero(p1)
  const z2 = isZero(p2)
  if (dimZero && z1 && z2) {
    // Still show the row but with dashes
  }
  return (
    <tr className="border-t border-slate-800 hover:bg-slate-800/30 transition-colors">
      <td className={`py-1.5 px-4 text-xs text-slate-300 ${indent ? 'pl-8' : ''}`}>
        {label}
      </td>
      <td className="py-1.5 px-4 text-xs text-right text-slate-200 tabular-nums w-36">
        {z1 ? '—' : fmtIndian(p1)}
      </td>
      <td className="py-1.5 px-4 text-xs text-right text-slate-200 tabular-nums w-36">
        {z2 ? '—' : fmtIndian(p2)}
      </td>
    </tr>
  )
}

function SubtotalRow({ label, p1, p2 }) {
  return (
    <tr className="border-t border-slate-500">
      <td className="py-2 px-4 text-xs font-semibold text-slate-100">{label}</td>
      <td className="py-2 px-4 text-xs text-right font-semibold text-slate-100 tabular-nums border-t border-slate-500 w-36">
        {fmtIndian(p1)}
      </td>
      <td className="py-2 px-4 text-xs text-right font-semibold text-slate-100 tabular-nums border-t border-slate-500 w-36">
        {fmtIndian(p2)}
      </td>
    </tr>
  )
}

function TotalRow({ label, p1, p2, highlight = false }) {
  const cls = highlight
    ? 'bg-amber-900/30 text-amber-200 border-t-2 border-amber-700'
    : 'bg-slate-700/40 text-slate-100 border-t-2 border-slate-500'
  return (
    <tr className={cls}>
      <td className="py-2 px-4 text-sm font-bold">{label}</td>
      <td className="py-2 px-4 text-sm font-bold text-right tabular-nums w-36">
        {fmtIndian(p1)}
      </td>
      <td className="py-2 px-4 text-sm font-bold text-right tabular-nums w-36">
        {fmtIndian(p2)}
      </td>
    </tr>
  )
}

function BlankRow() {
  return <tr className="h-2"><td colSpan={3} /></tr>
}

// ── Date pickers ───────────────────────────────────────────────────────────

function PeriodPicker({ label, fromVal, toVal, onFrom, onTo }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-slate-400 font-medium">{label}</span>
      <div className="flex items-center gap-2">
        <input
          type="month"
          value={fromVal}
          onChange={e => onFrom(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
        />
        <span className="text-slate-500 text-sm">→</span>
        <input
          type="month"
          value={toVal}
          onChange={e => onTo(e.target.value)}
          className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
        />
      </div>
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function CashFlowStatement() {
  const [p1From, setP1From] = useState('2025-04')
  const [p1To,   setP1To]   = useState('2025-12')
  const [p2From, setP2From] = useState('2025-04')
  const [p2To,   setP2To]   = useState('2026-01')
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [data,    setData]    = useState(null)

  async function generate() {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchCashFlow(p1From, p1To, p2From, p2To)
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const p1 = data?.periods?.[0]
  const p2 = data?.periods?.[1]

  return (
    <div className="max-w-screen-lg mx-auto px-6 py-6 space-y-6">
      {/* ── Header ── */}
      <div>
        <h2 className="text-xl font-bold text-slate-100">Statement of Cash Flows</h2>
        <p className="text-xs text-slate-400 mt-1">
          Unreal Estate Habitat Private Limited · CIN: U55100KA2024PTC191723
        </p>
      </div>

      {/* ── Date pickers ── */}
      <div className="bg-slate-900 border border-slate-700 rounded-xl p-5 flex flex-wrap items-end gap-6">
        <PeriodPicker
          label="Period 1"
          fromVal={p1From} toVal={p1To}
          onFrom={setP1From} onTo={setP1To}
        />
        <PeriodPicker
          label="Period 2"
          fromVal={p2From} toVal={p2To}
          onFrom={setP2From} onTo={setP2To}
        />
        <button
          onClick={generate}
          disabled={loading}
          className="ml-auto px-6 py-2 bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-sm font-semibold rounded-lg transition-colors"
        >
          {loading ? 'Generating…' : 'Generate'}
        </button>
      </div>

      {/* ── Error ── */}
      {error && (
        <div className="bg-red-900/40 border border-red-700 rounded-lg px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {/* ── Loading skeleton ── */}
      {loading && (
        <div className="bg-slate-900 border border-slate-700 rounded-xl p-8 text-center text-slate-400 text-sm animate-pulse">
          Fetching data from Tally…
        </div>
      )}

      {/* ── Table ── */}
      {p1 && p2 && !loading && (
        <div className="bg-[#0D1220] border border-slate-700 rounded-xl overflow-hidden">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-slate-800 border-b border-slate-600">
                <th className="py-3 px-4 text-left text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Particulars
                </th>
                <th className="py-3 px-4 text-right text-xs font-semibold text-amber-400 uppercase tracking-wider w-36">
                  {p1.label}
                </th>
                <th className="py-3 px-4 text-right text-xs font-semibold text-amber-400 uppercase tracking-wider w-36">
                  {p2.label}
                </th>
              </tr>
            </thead>
            <tbody>
              {/* ── OPERATING ── */}
              <SectionHeader label="Cash flow from Operating Activities" />
              <DataRow label="Net profit before taxation and extraordinary items"
                p1={p1.net_profit} p2={p2.net_profit} />
              <DataRow label="Add: Non-Cash/ Non-Operating Expenses" p1={null} p2={null} />
              <DataRow label="(a) Depreciation"   p1={null} p2={null} indent />
              <DataRow label="(b) Finance Costs"  p1={null} p2={null} indent />
              <DataRow label="(c) Provisions"     p1={null} p2={null} indent />
              <DataRow label="(d) Loss on sale of assets" p1={null} p2={null} indent />
              <BlankRow />
              <SubtotalRow label="Operating Profit before Working Capital Changes"
                p1={p1.net_profit} p2={p2.net_profit} />
              <BlankRow />
              <DataRow label="Working Capital Changes" p1={null} p2={null} />
              <DataRow label="(Increase)/Decrease in Current Assets"
                p1={p1.wc_current_assets} p2={p2.wc_current_assets} indent />
              <DataRow label="Increase/(Decrease) in Current Liabilities"
                p1={p1.wc_current_liabilities} p2={p2.wc_current_liabilities} indent />
              <BlankRow />
              <SubtotalRow label="Cash generated from Operations"
                p1={p1.operating} p2={p2.operating} />
              <DataRow label="Less: Income Tax Paid" p1={null} p2={null} indent />
              <TotalRow label="Net Cash flows from Operating Activities"
                p1={p1.operating} p2={p2.operating} />

              <BlankRow />

              {/* ── INVESTING ── */}
              <SectionHeader label="Cash flows from Investing Activities" />
              <DataRow label="Purchase of Property, Plant and Equipment"
                p1={p1.invest_fixed_assets} p2={p2.invest_fixed_assets} />
              <DataRow label="Sale of Property, Plant and Equipment" p1={null} p2={null} />
              <DataRow label="Changes in Long-term loans and advances"
                p1={p1.invest_loans_asset} p2={p2.invest_loans_asset} />
              <TotalRow label="Net Cash Utilized in Investing Activities"
                p1={p1.investing} p2={p2.investing} />

              <BlankRow />

              {/* ── FINANCING ── */}
              <SectionHeader label="Cash flows from Financing Activities" />
              <DataRow label="Finance costs"            p1={null} p2={null} />
              <DataRow label="Loans (Net)"
                p1={p1.fin_loans} p2={p2.fin_loans} />
              <DataRow label="Share capital money received"
                p1={isZero(p1.fin_capital) ? null : p1.fin_capital}
                p2={isZero(p2.fin_capital) ? null : p2.fin_capital} />
              <TotalRow label="Net Cash utilized in Financing Activities"
                p1={p1.financing} p2={p2.financing} />

              <BlankRow />

              {/* ── SUMMARY ── */}
              <TotalRow label="Net Increase/ Decrease in Cash & Cash Equivalents"
                p1={p1.net_change} p2={p2.net_change} />
              <DataRow label="Opening Balance of Cash & Cash Equivalents"
                p1={p1.opening_cash} p2={p2.opening_cash} />
              <TotalRow label="Closing Balance of Cash & Cash Equivalents"
                p1={p1.closing_cash} p2={p2.closing_cash} highlight />
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
