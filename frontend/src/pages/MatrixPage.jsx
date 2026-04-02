import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchReportData } from '../utils/api'
import MatrixReport from '../components/MatrixReport'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'

export default function MatrixPage() {
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
        const result = await fetchReportData('matrix', fromYM, toYM)
        if (active) setData(result.data.matrix_pnl)
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
        title="Building-Wise Matrix"
        sub={data?.[0]?.period}
        note="Scroll horizontally to view all properties →"
      />
      <MatrixReport matrixList={data} />
    </section>
  )
}
