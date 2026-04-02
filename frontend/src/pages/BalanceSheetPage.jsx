import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchReportData } from '../utils/api'
import BalanceSheet from '../components/BalanceSheet'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'

export default function BalanceSheetPage() {
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
        const result = await fetchReportData('balance-sheet', fromYM, toYM)
        if (active) setData(result.data.balance_sheet)
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
      <SectionTitle title="Balance Sheet" sub={data.period} />
      <BalanceSheet report={data} />
    </section>
  )
}
