import ReactDOM from 'react-dom/client'
import App from './App'
import ErrorBoundary from './ErrorBoundary'
import './styles.css'

// NEVER swallow errors: surface unhandled promise rejections + global errors
// (otherwise just a blank screen in the embedded viewer).
window.addEventListener('error', (e) => {
  const el = document.getElementById('global-error')
  if (el) { el.textContent = 'Error: ' + (e.message || e.error); el.style.display = 'block' }
})
window.addEventListener('unhandledrejection', (e) => {
  const el = document.getElementById('global-error')
  if (el) { el.textContent = 'Unhandled: ' + ((e.reason as Error)?.message || e.reason); el.style.display = 'block' }
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ErrorBoundary><App /></ErrorBoundary>,
)
