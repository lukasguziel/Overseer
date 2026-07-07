// Thin client for the plugin JSON API. Always relative /api paths
// (same origin when served by the plugin; via Vite proxy in dev).
export async function call<T = any>(op: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api/${op}`, {
    method: body ? 'POST' : 'GET',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let data: any
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(text || res.statusText)
  }
  if (!res.ok || data.error) {
    const err = new Error(data.error || res.statusText)
    ;(err as any).data = data     // keep extra fields (e.g. save_preset {exists,id})
    throw err
  }
  return data as T
}
