import { getMockData } from '../data/mockData'

function toTallyFrom(ym) {
  if (!ym) return '20250401'
  return ym.replace('-', '') + '01'
}

function toTallyTo(ym) {
  if (!ym) return '20260131'
  const [y, m] = ym.split('-').map(Number)
  const last = new Date(y, m, 0).getDate()
  return `${y}${String(m).padStart(2, '0')}${last}`
}

export async function fetchReportData(endpoint, fromYM, toYM) {
  const from = toTallyFrom(fromYM)
  const to   = toTallyTo(toYM)
  try {
    const res = await fetch(`/api/reports/${endpoint}/?from=${from}&to=${to}`, {
      signal: AbortSignal.timeout(180_000),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const json = await res.json()
    if (json.status === 'error') throw new Error(json.message)
    return { data: json.data, source: 'live' }
  } catch (e) {
    if (e?.name === 'TypeError' || e?.message?.includes('fetch')) {
      await new Promise((r) => setTimeout(r, 400))
      const mock = getMockData(from, to)
      // Map mock data keys correctly based on endpoint
      let key = null
      if (endpoint === 'pnl') key = 'consolidated_pnl'
      else if (endpoint === 'balance-sheet') key = 'balance_sheet'
      else if (endpoint === 'matrix') key = 'matrix_pnl'
      else if (endpoint === 'unit-wise') key = 'unit_wise'
      
      const mockEnvelope = {
        company_id: mock.company_id,
        company_name: mock.company_name,
        period_start: mock.period_start,
        period_end: mock.period_end,
        [key]: mock[key]
      }
      return { data: mockEnvelope, source: 'mock' }
    }
    throw e
  }
}
