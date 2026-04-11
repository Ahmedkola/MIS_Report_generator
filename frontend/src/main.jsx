import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './index.css'
import App from './App'

// HashRouter uses #/route URLs instead of /route — this is the only router
// that works when opening index.html directly via the file:// protocol
// (as the client does after extracting the downloaded ZIP).
document.addEventListener('DOMContentLoaded', () => {
  createRoot(document.getElementById('root')).render(
    <StrictMode>
      <HashRouter>
        <App />
      </HashRouter>
    </StrictMode>
  )
})
