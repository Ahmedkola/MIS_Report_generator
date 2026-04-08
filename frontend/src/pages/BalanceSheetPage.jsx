import { useReport } from '../context/ReportContext'
import BalanceSheet from '../components/BalanceSheet'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'

export default function BalanceSheetPage() {
  const { data, loading, error } = useReport()

  if (loading) return <LoadingState />
  if (error)   return <ErrorState error={error} />
  if (!data)   return <EmptyState />

  const bs = data.balance_sheet
  if (!bs)   return <EmptyState />

  return (
    <section>
      <SectionTitle title="Balance Sheet" sub={bs.period} />
      <BalanceSheet report={bs} />
    </section>
  )
}
