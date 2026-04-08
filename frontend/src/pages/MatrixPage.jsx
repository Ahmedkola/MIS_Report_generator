import { useReport } from '../context/ReportContext'
import MatrixReport from '../components/MatrixReport'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'

export default function MatrixPage() {
  const { data, loading, error } = useReport()

  if (loading) return <LoadingState />
  if (error)   return <ErrorState error={error} />
  if (!data)   return <EmptyState />

  const matrix = data.matrix_pnl
  if (!matrix) return <EmptyState />

  return (
    <section>
      <SectionTitle
        title="Building-Wise Matrix"
        sub={matrix?.[0]?.period}
        note="Scroll horizontally to view all properties →"
      />
      <MatrixReport matrixList={matrix} />
    </section>
  )
}
