import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    // Scope the service worker to the app path.
    navigator.serviceWorker.register('/app/sw.js', { scope: '/app/' }).catch(() => {
      // Non-fatal: installability will just be disabled.
    })
  })
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
)
