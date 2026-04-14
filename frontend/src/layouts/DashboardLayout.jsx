import { useState, useEffect } from 'react'
import { Outlet, useSearchParams } from 'react-router-dom'
import { useReport } from '../context/ReportContext'
import Header from '../components/Header'
import ReportTabs from '../components/ReportTabs'
import DateRangePicker from '../components/DateRangePicker'

export default function DashboardLayout() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { loading, generate, isOffline, data } = useReport()

  const initialFrom = searchParams.get('from') || '2025-04'
  const initialTo   = searchParams.get('to')   || '2026-01'

  const [fromYM, setFromYM] = useState(initialFrom)
  const [toYM,   setToYM]   = useState(initialTo)

  // Keep local picker state in sync when URL changes externally (e.g. browser back)
  useEffect(() => {
    setFromYM(searchParams.get('from') || '2025-04')
    setToYM(searchParams.get('to')     || '2026-01')
  }, [searchParams])

  const handlePickerChange = (field, value) => {
    if (field === 'from') setFromYM(value)
    else setToYM(value)
  }

  const handleGenerate = () => {
    // Update URL so tabs preserve the date range and the page is bookmarkable
    setSearchParams({ from: fromYM, to: toYM })
    // Fetch all reports at once, bust the server cache
    generate(fromYM, toYM, true)
  }

  // Derive actual Tally-format dates for the download URL
  const dlFrom = data?.period_start || fromYM.replace('-', '') + '01'
  const dlTo   = data?.period_end   || toYM.replace('-', '') + '28'

  // Human-readable period label shown in header, e.g. "Apr 2025 – Jan 2026"
  const fmtYM = (ym) => {
    if (!ym) return ''
    const [y, m] = ym.split('-')
    return new Date(Number(y), Number(m) - 1, 1).toLocaleString('en-IN', { month: 'short', year: 'numeric' })
  }
  const periodLabel = data && fromYM && toYM
    ? `${fmtYM(fromYM)} – ${fmtYM(toYM)}`
    : null

  return (
    <div className="min-h-screen bg-[#0A0F1E] text-slate-100">
      <Header fromDate={dlFrom} toDate={dlTo} loading={loading} periodLabel={periodLabel} />

      {/* Hide the date picker controls in offline snapshot mode */}
      {!isOffline && (
        <div className="border-b border-slate-800 bg-[#0D1220]">
          <div className="max-w-screen-2xl mx-auto px-6 py-4">
            <DateRangePicker
              from={fromYM}
              to={toYM}
              onChange={handlePickerChange}
              onGenerate={handleGenerate}
              loading={loading}
            />
          </div>
        </div>
      )}

      <ReportTabs />

      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-8">
        <Outlet />
      </main>

      <footer className="mt-16 pb-8 text-center text-xs text-slate-700">
        MIS Dashboard · Unreal Estate Habitat Pvt. Ltd.
      </footer>
    </div>
  )
}
