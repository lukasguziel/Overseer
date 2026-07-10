import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'
import { call } from '../api'

// Last successful result per audit op, shared across components so e.g. the
// area-score ring (useOrganizer) can read the tags scan the TagsTab loaded.
const cache = new Map<string, unknown>()
const listeners = new Set<() => void>()

// Every audit op that has been fetched at least once this session — the set
// the global "reload all areas" pass refreshes (no point rescanning tabs the
// user never opened).
const loadedOps = new Set<string>()

// Epoch bumped whenever the shared cache is refreshed in bulk, so the audit
// tabs (which keep their own local copy) re-sync from the cache.
let epoch = 0
const epochListeners = new Set<() => void>()

export function subscribeEpoch(cb: () => void): () => void {
  epochListeners.add(cb)
  return () => { epochListeners.delete(cb) }
}

function publish(op: string, data: unknown) {
  cache.set(op, data)
  loadedOps.add(op)
  listeners.forEach((l) => l())
}

// Re-run every audit scan the user has already loaded this session, publishing
// fresh results into the shared cache. Sequential so the scans do not fight
// over the single C4D main thread; `onStep(op)` fires before each one so the
// caller can drive a progress readout. Bumps the epoch at the end so open
// audit tabs pick up their new data.
export async function refreshLoadedAudits(onStep?: (op: string) => void): Promise<void> {
  const ops = Array.from(loadedOps)
  for (const op of ops) {
    onStep?.(op)
    try {
      const r = await call(op)
      cache.set(op, r)
    } catch { /* keep the last good scan for this op */ }
  }
  epoch += 1
  epochListeners.forEach((l) => l())
  listeners.forEach((l) => l())
}

export function loadedAuditCount(): number {
  return loadedOps.size
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
  const [data, setData] = useState<T | null>(() => (cache.get(op) as T | undefined) ?? null)
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

  // A global "reload all areas" pass refreshes the shared cache off-tab; pick
  // up the fresh scan so this tab shows current data without a manual reload.
  useEffect(() => subscribeEpoch(() => {
    const c = cache.get(op)
    if (c !== undefined) setData(c as T)
  }), [op])

  return { data, loading, error, reload }
}
