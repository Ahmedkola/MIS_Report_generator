import { ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { formatCurrency } from '../../utils/formatters'

export default function ComposedTrendCard({ title, data, dataKeyX, barDataKey, lineDataKey, barColor = "#1E293B", lineColor = "#34D399" }) {
  if (!data || data.length === 0) return null

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 flex flex-col h-[320px]">
      <h3 className="text-sm font-semibold tracking-wide text-slate-300 mb-4 uppercase">{title}</h3>
      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
            <XAxis
              dataKey={dataKeyX}
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              dy={8}
            />
            <YAxis
              yAxisId="left"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => {
                if (value >= 10000000) return `${(value / 10000000).toFixed(1)}Cr`
                if (value >= 100000) return `${(value / 100000).toFixed(1)}L`
                if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
                return value
              }}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => {
                if (value >= 10000000) return `${(value / 10000000).toFixed(1)}Cr`
                if (value >= 100000) return `${(value / 100000).toFixed(1)}L`
                if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
                return value
              }}
            />
            <Tooltip
              formatter={(value, name) => [formatCurrency(value), name]}
              cursor={{ fill: '#1E293B', opacity: 0.4 }}
              contentStyle={{ backgroundColor: '#0D1220', borderColor: '#1E293B', borderRadius: '0.5rem', color: '#CBD5E1' }}
              itemStyle={{ color: '#E2E8F0', fontVariantNumeric: 'tabular-nums' }}
            />
            <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: '11px', color: '#94A3B8' }} />
            <Bar
              yAxisId="left"
              dataKey={barDataKey}
              fill={barColor}
              radius={[4, 4, 0, 0]}
              animationDuration={800}
            />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey={lineDataKey}
              stroke={lineColor}
              strokeWidth={3}
              dot={{ r: 4, fill: '#111827', strokeWidth: 2 }}
              activeDot={{ r: 6 }}
              animationDuration={1000}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
