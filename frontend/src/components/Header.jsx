export default function Header() {
  return (
    <header className="border-b border-slate-800 bg-[#0A0F1E]/80 backdrop-blur sticky top-0 z-30">
      <div className="max-w-screen-2xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-gold to-gold-dark flex items-center justify-center shrink-0">
            <svg className="w-5 h-5 text-[#0A0F1E]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.5l9-9 9 9M4.5 12v7.5h5V15h5v4.5h5V12" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100 leading-tight">
              MIS Dashboard
            </h1>
          </div>
        </div>
        
        <button 
          onClick={() => window.print()}
          className="print:hidden flex items-center gap-2 bg-[#1E293B] hover:bg-[#334155] border border-slate-700 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export PDF
        </button>
      </div>
    </header>
  )
}
