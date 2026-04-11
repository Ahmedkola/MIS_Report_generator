import { Routes, Route, Navigate } from 'react-router-dom'
import { ReportDataProvider } from './context/ReportContext'
import DashboardLayout from './layouts/DashboardLayout'
import PnLPage from './pages/PnLPage'
import BalanceSheetPage from './pages/BalanceSheetPage'
import MatrixPage from './pages/MatrixPage'
import UnitWisePage from './pages/UnitWisePage'
import CashFlowPage from './pages/CashFlowPage'

export default function App() {
  return (
    <ReportDataProvider>
      <Routes>
        <Route path="/" element={<DashboardLayout />}>
          <Route index element={<Navigate to="/pnl" replace />} />
          <Route path="pnl"          element={<PnLPage />} />
          <Route path="balance-sheet" element={<BalanceSheetPage />} />
          <Route path="matrix"        element={<MatrixPage />} />
          <Route path="unit-wise"     element={<UnitWisePage />} />
          <Route path="cash-flow"     element={<CashFlowPage />} />
        </Route>
      </Routes>
    </ReportDataProvider>
  )
}
