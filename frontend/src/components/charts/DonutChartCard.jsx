import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { formatCurrency } from '../../utils/formatters'

export default function DonutChartCard({ title, data, colors }) {
  if (!data || data.length === 0) return null

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 flex flex-col h-[320px]">
      <h3 className="text-sm font-semibold tracking-wide text-slate-300 mb-4 uppercase">{title}</h3>
      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              innerRadius="60%"
              outerRadius="90%"
              paddingAngle={4}
              dataKey="value"
              stroke="none"
              animationBegin={0}
              animationDuration={800}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => formatCurrency(value)}
              contentStyle={{ backgroundColor: '#0D1220', borderColor: '#1E293B', borderRadius: '0.5rem', color: '#CBD5E1' }}
              itemStyle={{ color: '#E2E8F0', fontVariantNumeric: 'tabular-nums' }}
            />
            <Legend verticalAlign="bottom" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px', color: '#94A3B8' }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
