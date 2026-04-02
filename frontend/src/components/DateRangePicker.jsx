export default function DateRangePicker({ from, to, onChange, onGenerate, loading }) {
  return (
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
  )
}
