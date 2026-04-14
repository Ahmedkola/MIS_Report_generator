export function SectionTitle({ title, sub, note }) {
  return (
    <div className="mb-5 border-l-4 border-gold pl-3">
      <h2 className="text-base font-semibold text-slate-100">{title}</h2>
      <div className="flex flex-wrap items-center gap-3 mt-0.5">
        {sub && <span className="text-xs text-slate-500 font-mono">{sub}</span>}
        {note && <span className="text-xs text-slate-600 italic">{note}</span>}
      </div>
    </div>
  )
}

export function LoadingState() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-sm text-slate-400 px-1">
        <svg className="w-4 h-4 animate-spin text-gold shrink-0" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
        </svg>
        Fetching from TallyPrime...
      </div>
      <div className="animate-pulse space-y-3">
        <div className="h-20 bg-slate-800/50 rounded-xl" />
        <div className="h-64 bg-slate-800/30 rounded-xl" />
        <div className="h-32 bg-slate-800/20 rounded-xl" />
      </div>
    </div>
  )
}

export function ErrorState({ error }) {
  return (
    <div className="rounded-xl border border-rose-900 bg-rose-950/20 px-6 py-5 text-rose-300 text-sm">
      <p className="font-semibold mb-1">Failed to generate report</p>
      <p className="text-rose-400/70 font-mono text-xs">{error}</p>
    </div>
  )
}

export function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-14 h-14 rounded-2xl bg-slate-800 flex items-center justify-center mb-5">
        <svg className="w-7 h-7 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.5l9-9 9 9M4.5 12v7.5h5V15h5v4.5h5V12" />
        </svg>
      </div>
      <p className="text-slate-400 font-medium mb-1">No report generated yet</p>
      <p className="text-slate-600 text-sm">Select a date range above and click Generate Report</p>
    </div>
  )
}
