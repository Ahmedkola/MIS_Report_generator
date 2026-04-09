import { useReport } from '../context/ReportContext'
import PnLReport from '../components/PnLReport'
import SummaryCards from '../components/SummaryCards'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'

export default function PnLPage() {
  const { data, loading, error } = useReport()

  if (loading) return <LoadingState />
  if (error)   return <ErrorState error={error} />
  if (!data)   return <EmptyState />

  const pnl = data.consolidated_pnl
  if (!pnl)  return <EmptyState />

  return (
    <section>
      <SummaryCards pnl={pnl} matrix={null} />
      <SectionTitle title="Consolidated Profit & Loss" sub={pnl.period} />
      <PnLReport report={pnl} />
    </section>
  )
}

