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
      </div>
    </header>
  )
}
