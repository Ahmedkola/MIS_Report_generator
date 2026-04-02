import { Routes, Route, Navigate } from 'react-router-dom'
import DashboardLayout from './layouts/DashboardLayout'
import PnLPage from './pages/PnLPage'
import BalanceSheetPage from './pages/BalanceSheetPage'
import MatrixPage from './pages/MatrixPage'
import UnitWisePage from './pages/UnitWisePage'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<DashboardLayout />}>
        {/* Redirect root to P&L */}
        <Route index element={<Navigate to="/pnl" replace />} />
        
        <Route path="pnl" element={<PnLPage />} />
        <Route path="balance-sheet" element={<BalanceSheetPage />} />
        <Route path="matrix" element={<MatrixPage />} />
        <Route path="unit-wise" element={<UnitWisePage />} />
      </Route>
    </Routes>
  )
}
