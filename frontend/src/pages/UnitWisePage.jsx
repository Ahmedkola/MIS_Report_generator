import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchReportData } from '../utils/api'
import UnitWiseReport from '../components/UnitWiseReport'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'

export default function UnitWisePage() {
  const [searchParams] = useSearchParams()
  const fromYM = searchParams.get('from')
  const toYM = searchParams.get('to')

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const result = await fetchReportData('unit-wise', fromYM, toYM)
        if (active) setData(result.data.unit_wise)
      } catch (e) {
        if (active) setError(e.message)
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [fromYM, toYM])

  if (loading) return <LoadingState />
  if (error) return <ErrorState error={error} />
  if (!data) return <EmptyState />

  return (
    <section>
      <SectionTitle
        title="Unit-Wise P&L"
        sub={data?.period}
        note="Scroll horizontally to view all units →"
      />
      <UnitWiseReport report={data} />
    </section>
  )
}
