import React from 'react'

// Faengt Render-Fehler ab und zeigt sie an, statt eine leere Seite zu
// hinterlassen (im eingebetteten QtWebEngine sieht man sonst nur "kurz da,
// dann nichts"). Zeigt Fehlermeldung + Stack + Reload-Button.
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { error: null, info: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    this.setState({ info })
    // Auch in die JS-Konsole, falls jemand die DevTools offen hat.
    console.error('[SceneOrganizer] render error:', error, info)
  }

  render() {
    const { error, info } = this.state
    if (!error) return this.props.children
    return (
      <div className="crash">
        <h1>⚠ Something crashed the UI</h1>
        <p className="crash-msg">{String(error && error.message || error)}</p>
        {info?.componentStack && (
          <pre className="crash-stack">{info.componentStack}</pre>
        )}
        {error?.stack && <pre className="crash-stack">{error.stack}</pre>}
        <button onClick={() => { this.setState({ error: null, info: null }); location.reload() }}>
          Reload
        </button>
      </div>
    )
  }
}
