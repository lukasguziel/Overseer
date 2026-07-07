import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import './styles.css'

// Fehler NIE verschlucken: unbehandelte Promise-Rejections + globale Fehler
// sichtbar machen (sonst nur leerer Screen im eingebetteten Viewer).
window.addEventListener('error', (e) => {
  const el = document.getElementById('global-error')
  if (el) { el.textContent = 'Error: ' + (e.message || e.error); el.style.display = 'block' }
})
window.addEventListener('unhandledrejection', (e) => {
  const el = document.getElementById('global-error')
  if (el) { el.textContent = 'Unhandled: ' + (e.reason?.message || e.reason); el.style.display = 'block' }
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <ErrorBoundary><App /></ErrorBoundary>,
)
