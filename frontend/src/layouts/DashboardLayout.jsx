import { useState, useEffect } from 'react'
import { Outlet, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import Header from '../components/Header'
import ReportTabs from '../components/ReportTabs'
import DateRangePicker from '../components/DateRangePicker'

export default function DashboardLayout() {
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  
  const initialFrom = searchParams.get('from') || '2025-04'
  const initialTo = searchParams.get('to') || '2026-01'
  
  const [fromYM, setFromYM] = useState(initialFrom)
  const [toYM, setToYM]     = useState(initialTo)

  useEffect(() => {
    setFromYM(searchParams.get('from') || '2025-04')
    setToYM(searchParams.get('to') || '2026-01')
  }, [searchParams])

  const handlePickerChange = (field, value) => {
    if (field === 'from') setFromYM(value)
    else setToYM(value)
  }

  const navigate = useNavigate()

  const generate = () => {
    setSearchParams({ from: fromYM, to: toYM })
  }

  return (
    <div className="min-h-screen bg-[#0A0F1E] text-slate-100">
      <Header />

      <div className="border-b border-slate-800 bg-[#0D1220]">
        <div className="max-w-screen-2xl mx-auto px-6 py-4">
          <DateRangePicker
            from={fromYM}
            to={toYM}
            onChange={handlePickerChange}
            onGenerate={generate}
            loading={false}
          />
        </div>
      </div>

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
