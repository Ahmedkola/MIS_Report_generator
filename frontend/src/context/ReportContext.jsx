import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { fetchAllData } from '../utils/api'

const ReportContext = createContext(null)

export function ReportDataProvider({ children }) {
  // ── OFFLINE MODE DETECTION ────────────────────────────────────────────────
  // When the user opens the downloaded ZIP, the backend injects the full
  // report data as: <script>window.REPORT_DATA = {...};</script>
  // We detect this at startup and skip all API calls entirely.
  const isOffline = typeof window !== 'undefined' && !!window.REPORT_DATA

  const [data,    setData]    = useState(isOffline ? window.REPORT_DATA : null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)
  const [source,  setSource]  = useState(isOffline ? 'offline' : null)
  const abortRef = useRef(null)

  const generate = useCallback(async (fromYM, toYM, bust = true) => {
    // In offline mode data is already pre-loaded — nothing to do
    if (isOffline) return

    // Cancel any in-flight request
    if (abortRef.current) abortRef.current.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setLoading(true)
    setError(null)

    try {
      const result = await fetchAllData(fromYM, toYM, bust, controller.signal)
      if (!controller.signal.aborted) {
        setData(result.data)
        setSource(result.source)
      }
    } catch (e) {
      if (!controller.signal.aborted) {
        setError(e.message)
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false)
      }
    }
  }, [isOffline])

  return (
    <ReportContext.Provider value={{ data, loading, error, source, generate, isOffline }}>
      {children}
    </ReportContext.Provider>
  )
}

export function useReport() {
  const ctx = useContext(ReportContext)
  if (!ctx) throw new Error('useReport must be used inside <ReportDataProvider>')
  return ctx
}
