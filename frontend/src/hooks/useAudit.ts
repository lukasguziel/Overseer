import { useCallback, useEffect, useState } from 'react'
import { call } from '../api'

// Shared data loader for the audit tabs (Tags / Generators / Files / Sims):
// fetches `<op>` when the tab becomes active, exposes loading/error and a
// manual reload for after an action. Keeps every audit tab identical in
// behavior without touching the central useOrganizer hook.
export default function useAudit<T>(op: string, active: boolean) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setData(await call<T>(op))
    } catch (e: any) {
      setError(String(e.message || e))
    } finally {
      setLoading(false)
    }
  }, [op])

  useEffect(() => {
    if (active && data === null) reload()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, reload])

  return { data, loading, error, reload }
}
