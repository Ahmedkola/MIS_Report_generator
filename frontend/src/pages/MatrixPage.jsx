import { useReport } from '../context/ReportContext'
import MatrixReport from '../components/MatrixReport'
import { SectionTitle, LoadingState, ErrorState, EmptyState } from '../components/Shared'
import BarChartCard from '../components/charts/BarChartCard'
import ComposedTrendCard from '../components/charts/ComposedTrendCard'

export default function MatrixPage() {
  const { data, loading, error } = useReport()

  if (loading) return <LoadingState />
  if (error)   return <ErrorState error={error} />
  if (!data)   return <EmptyState />

  const matrix = data.matrix_pnl
  if (!matrix || matrix.length === 0) return <EmptyState />

  const latestMatrix = matrix[0]
  const dataCols = Object.keys(latestMatrix?.rows[0]?.cost_centers ?? {}).filter(c => c !== 'Total')

  const chartData = dataCols.map(col => {
    const revRow = latestMatrix.rows.find(r => r.row_name === 'Net Sales' || r.row_name === 'Gross Sales')
    const ebitdaRow = latestMatrix.rows.find(r => r.row_name === 'EBIDTA')

    return {
      name: col,
      Revenue: revRow?.cost_centers?.[col] || 0,
      EBITDA: ebitdaRow?.cost_centers?.[col] || 0
    }
  }).filter(d => d.Revenue !== 0 || d.EBITDA !== 0)

  const revenueChartData = [...chartData].sort((a, b) => b.Revenue - a.Revenue)

  return (
    <section>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-6">
        <BarChartCard 
          title="Revenue per Property" 
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
        title="Building-Wise Matrix"
        sub={latestMatrix?.period}
        note="Scroll horizontally to view all properties →"
      />
      <MatrixReport matrixList={matrix} />
    </section>
  )
}

