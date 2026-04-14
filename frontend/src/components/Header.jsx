import { useReport } from '../context/ReportContext'

export default function Header({ fromDate, toDate, loading, periodLabel }) {
  const { isOffline } = useReport()

  // Build the download URL using the current report dates
  const dlFrom = fromDate || '20250401'
  const dlTo   = toDate   || '20260131'
  const downloadUrl = `/api/reports/download/?from=${dlFrom}&to=${dlTo}`

  return (
    <header className="border-b border-slate-800 bg-[#0A0F1E]/80 backdrop-blur sticky top-0 z-30 relative">
      <div className="max-w-screen-2xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-[#0A0F1E] border border-gold/40 flex items-center justify-center shrink-0 shadow-lg shadow-amber-900/20">
            <span className="text-gold font-bold text-lg leading-none tracking-tight select-none">M</span>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100 leading-tight">
              MIS Dashboard
            </h1>
            {isOffline ? (
              <span className="text-xs text-amber-400 font-medium">● Offline Snapshot</span>
            ) : periodLabel ? (
              <span className="text-xs text-slate-500 font-mono">{periodLabel}</span>
            ) : null}
          </div>
        </div>

        <div className="print:hidden flex items-center gap-3">
          {/* Download Report as offline ZIP — hidden when already in offline/ZIP mode */}
          {!isOffline && (
            <a
              id="download-report-btn"
              href={downloadUrl}
              download
              className="flex items-center gap-2 bg-[#C9A84C]/10 hover:bg-[#C9A84C]/20 border border-[#C9A84C]/40 text-[#C9A84C] px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download Report
            </a>
          )}
        </div>
      </div>

      {/* Loading progress bar at bottom of header */}
      {loading && (
        <div className="absolute bottom-0 left-0 w-full h-[2px] bg-gradient-to-r from-gold via-gold-light to-gold animate-pulse" />
      )}
    </header>
  )
}
