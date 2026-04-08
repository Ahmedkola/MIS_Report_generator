import { useReport } from '../context/ReportContext'
import UnitWiseReport from '../components/UnitWiseReport'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'

export default function UnitWisePage() {
  const { data, loading, error } = useReport()

  if (loading) return <LoadingState />
  if (error)   return <ErrorState error={error} />
  if (!data)   return <EmptyState />

  const unit = data.unit_wise
  if (!unit)  return <EmptyState />

  return (
    <section>
      <SectionTitle
        title="Unit-Wise P&L"
        sub={unit?.period}
        note="Scroll horizontally to view all units →"
      />
      <UnitWiseReport report={unit} />
    </section>
  )
}
