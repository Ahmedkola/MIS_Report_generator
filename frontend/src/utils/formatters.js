const INR = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const INR_DECIMAL = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function formatCurrency(value, decimals = false) {
  if (value == null || isNaN(value)) return '—'
  return decimals ? INR_DECIMAL.format(value) : INR.format(value)
}

export function formatPercent(value) {
  if (value == null || isNaN(value)) return '—'
  return `${value.toFixed(1)}%`
}

export function formatDate(yyyymmdd) {
  if (!yyyymmdd || yyyymmdd.length !== 8) return yyyymmdd
  const y = yyyymmdd.slice(0, 4)
  const m = yyyymmdd.slice(4, 6)
  const d = yyyymmdd.slice(6, 8)
  return new Date(`${y}-${m}-${d}`).toLocaleDateString('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

export function amountClass(value) {
  if (value > 0) return 'text-emerald-400'
  if (value < 0) return 'text-rose-400'
  return 'text-slate-400'
}

export function absAmount(value) {
  return Math.abs(value)
}
