const NUM_UNITS = ['', 'K', 'M', 'B']

const numShown = (v: number): string => v.toFixed(v >= 10 ? 0 : 1)

// The unit is chosen from the ROUNDED value, so 999_950 reads "1.0M", never
// "1000.0K".
export function humanNum(n: number | undefined | null): string {
  const v = n || 0
  let x = v
  let i = 0
  while (i < NUM_UNITS.length - 1 && Number(numShown(x)) >= 1000) { x /= 1e3; i++ }
  return i === 0 ? String(v) : numShown(x) + NUM_UNITS[i]
}

const BYTE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB']

const byteShown = (v: number, i: number): string => v.toFixed(v >= 100 || i === 0 ? 0 : 1)

export function humanBytes(b: number | undefined | null): string {
  if (!b) return '—'
  let v = b
  let i = 0
  while (i < BYTE_UNITS.length - 1 && Number(byteShown(v, i)) >= 1024) { v /= 1024; i++ }
  return byteShown(v, i) + ' ' + BYTE_UNITS[i]
}
