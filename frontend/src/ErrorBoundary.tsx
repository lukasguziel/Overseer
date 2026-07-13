import React, { type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
}
interface State {
  error: Error | null
  info: ErrorInfo | null
}

// Catches render errors and displays them instead of leaving a blank page
// (in the embedded QtWebEngine you otherwise only see "briefly there,
// then nothing"). Shows error message + stack + reload button.
export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null, info: null }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    this.setState({ info })
    // Also log to the JS console in case someone has the DevTools open.
    console.error('[Overseer] render error:', error, info)
  }

  render() {
    const { error, info } = this.state
    if (!error) return this.props.children
    return (
      <div className="crash">
        <h1>⚠ Something crashed the UI</h1>
        <p className="crash-msg">{String(error.message || error)}</p>
        {info?.componentStack && (
          <pre className="crash-stack">{info.componentStack}</pre>
        )}
        {error.stack && <pre className="crash-stack">{error.stack}</pre>}
        <button onClick={() => { this.setState({ error: null, info: null }); location.reload() }}>
          Reload
        </button>
      </div>
    )
  }
}
