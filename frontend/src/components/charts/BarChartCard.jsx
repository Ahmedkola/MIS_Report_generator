import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { formatCurrency } from '../../utils/formatters'

export default function BarChartCard({ title, data, dataKeyX, dataKeyY, color = "#C9A84C", barRadius = [4, 4, 0, 0] }) {
  if (!data || data.length === 0) return null

  // Function to determine color dynamically if color is a function, otherwise use the string given
  const getCellFill = (entry, index) => {
    if (typeof color === 'function') {
      return color(entry, index);
    }
    return color;
  };

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-xl p-5 flex flex-col h-[320px]">
      <h3 className="text-sm font-semibold tracking-wide text-slate-300 mb-4 uppercase">{title}</h3>
      <div className="flex-1 w-full min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
              formatter={(value) => [formatCurrency(value), '']}
              cursor={{ fill: '#1E293B', opacity: 0.4 }}
              contentStyle={{ backgroundColor: '#0D1220', borderColor: '#1E293B', borderRadius: '0.5rem', color: '#CBD5E1' }}
              itemStyle={{ color: '#E2E8F0', fontVariantNumeric: 'tabular-nums' }}
            />
            <Bar
              dataKey={dataKeyY}
              radius={barRadius}
              animationDuration={800}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getCellFill(entry, index)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
