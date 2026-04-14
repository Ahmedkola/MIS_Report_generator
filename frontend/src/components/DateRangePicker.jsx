const PRESETS = [
  {
    label: 'Last M',
    compute() {
      const now = new Date()
      const last = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      return { from: fmt(last), to: fmt(last) }
    },
  },
  {
    label: 'Last 3M',
    compute() {
      const now = new Date()
      const to = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const from = new Date(to.getFullYear(), to.getMonth() - 2, 1)
      return { from: fmt(from), to: fmt(to) }
    },
  },
  {
    label: 'Last 6M',
    compute() {
      const now = new Date()
      const to = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      const from = new Date(to.getFullYear(), to.getMonth() - 5, 1)
      return { from: fmt(from), to: fmt(to) }
    },
  },
  {
    label: 'YTD',
    compute() {
      const now = new Date()
      // Indian FY starts April; if current month < April, YTD is from Apr of last year
      const fyStart = now.getMonth() >= 3
        ? new Date(now.getFullYear(), 3, 1)        // Apr this year
        : new Date(now.getFullYear() - 1, 3, 1)   // Apr last year
      const to = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      return { from: fmt(fyStart), to: fmt(to) }
    },
  },
  {
    label: 'Last FY',
    compute() {
      const now = new Date()
      // Last FY: Apr (year-1) → Mar (year) if current month >= Apr, else Apr (year-2) → Mar (year-1)
      const fyEndYear = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1
      const from = new Date(fyEndYear - 1, 3, 1)  // Apr of previous year
      const to   = new Date(fyEndYear,     2, 1)  // Mar of end year
      return { from: fmt(from), to: fmt(to) }
    },
  },
]

function fmt(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
}

export default function DateRangePicker({ from, to, onChange, onGenerate, loading }) {
  const applyPreset = (preset) => {
    const { from: f, to: t } = preset.compute()
    onChange('from', f)
    onChange('to', t)
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Quick preset pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-[10px] text-slate-600 tracking-widest uppercase mr-1">Quick Select:</span>
        {PRESETS.map((p) => (
          <button
            key={p.label}
            onClick={() => applyPreset(p)}
            disabled={loading}
            className="text-xs rounded-full px-3 py-1 border border-slate-700 text-slate-400
                       hover:border-gold/60 hover:text-gold transition-colors
                       disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Manual inputs + Generate */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 tracking-widest uppercase">From</label>
          <input
            type="month"
            value={from}
            min="2020-01"
            max={to}
            onChange={(e) => onChange('from', e.target.value)}
            disabled={loading}
            className="bg-[#111827] border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200
                       focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold/30
                       disabled:opacity-40 disabled:cursor-not-allowed
                       [color-scheme:dark] min-w-[150px]"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[10px] text-slate-500 tracking-widest uppercase">To</label>
          <input
            type="month"
            value={to}
            min={from}
            max="2099-12"
            onChange={(e) => onChange('to', e.target.value)}
            disabled={loading}
            className="bg-[#111827] border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200
                       focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold/30
                       disabled:opacity-40 disabled:cursor-not-allowed
                       [color-scheme:dark] min-w-[150px]"
          />
        </div>

        <button
          onClick={onGenerate}
          disabled={loading || !from || !to}
          className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold
                     bg-gold text-[#0A0F1E] hover:bg-gold-light
                     disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors shadow-lg shadow-amber-900/30"
        >
          {loading ? (
            <>
              <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
              </svg>
              Generating…
            </>
          ) : (
            <>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
              </svg>
              Generate Report
            </>
          )}
        </button>

        {loading && (
          <p className="text-xs text-slate-500 italic self-center">
            Fetching from TallyPrime — this may take ~60s
          </p>
        )}
      </div>
    </div>
  )
}
