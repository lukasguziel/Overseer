// Duenner Client fuer die Plugin-JSON-API. Immer relative /api-Pfade
// (gleiche Origin, wenn vom Plugin ausgeliefert; im Dev via Vite-Proxy).
export async function call(op, body) {
  const res = await fetch(`/api/${op}`, {
    method: body ? 'POST' : 'GET',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let data
  try {
    data = text ? JSON.parse(text) : {}
  } catch {
    throw new Error(text || res.statusText)
  }
  if (!res.ok || data.error) throw new Error(data.error || res.statusText)
  return data
}
