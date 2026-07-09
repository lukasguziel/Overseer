import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'
import { call } from '../api'

// Last successful result per audit op, shared across components so e.g. the
// area-score ring (useOrganizer) can read the tags scan the TagsTab loaded.
const cache = new Map<string, unknown>()
const listeners = new Set<() => void>()

function publish(op: string, data: unknown) {
  cache.set(op, data)
  listeners.forEach((l) => l())
}

// Fire-and-forget prefetch into the shared cache (e.g. the Overview loads
// the tags scan so its score ring fills without visiting the Tags tab).
// Does nothing if a result is already cached.
export function prefetchAudit(op: string): void {
  if (cache.has(op)) return
  call(op).then((r) => publish(op, r)).catch(() => { /* score stays pending */ })
}

// Read-only subscription to the latest cached result of an audit op
// (null until the owning tab has run the scan at least once).
export function useAuditData<T>(op: string): T | null {
  return useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb) },
    () => (cache.get(op) as T | undefined) ?? null,
  )
}

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
      const r = await call<T>(op)
      setData(r)
      publish(op, r)
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
