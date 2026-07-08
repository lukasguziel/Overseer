// Git-style inline character diff for rename previews: the shared
// prefix/suffix stays plain, the changed middle is highlighted (red on the
// old name, green on the new one).
export interface DiffParts {
  prefix: string
  oldMid: string
  newMid: string
  suffix: string
}

export function diffParts(oldS: string, newS: string): DiffParts {
  let p = 0
  const maxP = Math.min(oldS.length, newS.length)
  while (p < maxP && oldS[p] === newS[p]) p++
  let s = 0
  const maxS = Math.min(oldS.length, newS.length) - p
  while (s < maxS && oldS[oldS.length - 1 - s] === newS[newS.length - 1 - s]) s++
  return {
    prefix: oldS.slice(0, p),
    oldMid: oldS.slice(p, oldS.length - s),
    newMid: newS.slice(p, newS.length - s),
    suffix: oldS.slice(oldS.length - s),
  }
}

export function DiffOld({ oldS, newS }: { oldS: string; newS: string }) {
  const d = diffParts(oldS, newS)
  if (!d.oldMid && !d.newMid) return <>{oldS}</>
  return (
    <>{d.prefix}{d.oldMid && <mark className="df-del">{d.oldMid}</mark>}{d.suffix}</>
  )
}

export function DiffNew({ oldS, newS }: { oldS: string; newS: string }) {
  const d = diffParts(oldS, newS)
  if (!d.oldMid && !d.newMid) return <>{newS}</>
  return (
    <>{d.prefix}{d.newMid && <mark className="df-add">{d.newMid}</mark>}{d.suffix}</>
  )
}
