import { useReport } from '../context/ReportContext'
import UnitWiseReport from '../components/UnitWiseReport'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'
import BarChartCard from '../components/charts/BarChartCard'
import ComposedTrendCard from '../components/charts/ComposedTrendCard'
import { formatPeriod } from '../utils/formatters'

export default function UnitWisePage() {
  const { data, loading, error } = useReport()

  if (loading) return <LoadingState />
  if (error)   return <ErrorState error={error} />
  if (!data)   return <EmptyState />

  const unit = data.unit_wise
  if (!unit)  return <EmptyState />

  const activeUnits = unit.columns
    .filter(([, bldg]) => bldg !== 'General')
    .map(([d]) => d)
    .filter((disp) => {
      const d = unit.data[disp]
      if (!d) return false
      return (d.gross_sales || 0) !== 0 || (d.total_direct_exp || 0) !== 0 || (d.total_indirect_exp || 0) !== 0
    })

  const chartData = activeUnits.map(disp => {
    const d = unit.data[disp] || {}
    return {
      name: disp,
      Revenue: d.net_revenue || 0,
      EBITDA: d.ebitda || 0
    }
  })

  // Sort by revenue descending for the bar chart
  const revenueChartData = [...chartData].sort((a, b) => b.Revenue - a.Revenue)

  return (
    <section>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-6">
        <BarChartCard 
          title="Revenue per Unit" 
          data={revenueChartData} 
          dataKeyX="name" 
          dataKeyY="Revenue" 
          color="#3B82F6" 
        />
        <ComposedTrendCard 
          title="Revenue vs EBITDA Trend" 
          data={chartData} 
          dataKeyX="name" 
          barDataKey="Revenue" 
          lineDataKey="EBITDA" 
          barColor="#1E293B" 
          lineColor="#C9A84C"
        />
      </div>

      <SectionTitle
        title="Unit-Wise P&L"
        sub={formatPeriod(unit?.period)}
        note="Scroll horizontally to view all units →"
      />
      <UnitWiseReport report={unit} />
    </section>
  )
}
