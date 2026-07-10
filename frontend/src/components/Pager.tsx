import { useRef, useState } from 'react'

export const PAGE_SIZE = 25
export const PAGE_SIZES = [10, 25, 50, 100]

export interface PagerState {
  page: number
  pages: number
  setPage: (p: number) => void
  total: number
  perPage: number
  setPerPage: (n: number) => void
}

// Shared pagination for every preview/list: prev/next plus a rows-per-page
// selector (10/25/50/100). The `perPage` argument is only the INITIAL page
// size — the selector then owns it as live state. The page index self-clamps
// when the list shrinks (apply/filter) or the page size grows. Lists with user
// filters additionally pass a `resetKey` (the filter state, e.g. joined into a
// string): whenever it changes the pager jumps back to page 1 — staying on
// page 3 of a freshly filtered list is never what you want.
export function usePager<T>(items: T[], perPage: number = PAGE_SIZE, resetKey?: unknown):
    PagerState & { rows: T[] } {
  const [rawPage, setPage] = useState(0)
  const [size, setPerPage] = useState(perPage)
  const lastKey = useRef(resetKey)
  if (!Object.is(lastKey.current, resetKey)) {
    // Render-phase state adjustment (the React-sanctioned pattern for
    // "reset state when an input changes").
    lastKey.current = resetKey
    if (rawPage !== 0) setPage(0)
  }
  const pages = Math.max(1, Math.ceil(items.length / size))
  const page = Math.min(rawPage, pages - 1)
  return {
    rows: items.slice(page * size, (page + 1) * size),
    page, pages, setPage, total: items.length, perPage: size, setPerPage,
  }
}

export default function Pager({ pager }: { pager: PagerState }) {
  const { page, pages, setPage, total, perPage, setPerPage } = pager
  // Nothing to page and nothing to resize away from the smallest option -> hide.
  if (total <= PAGE_SIZES[0]) return null
  return (
    <div className="pager">
      {pages > 1 && (
        <span className="pager-nav">
          <button className="pager-btn" disabled={page === 0}
            onClick={() => setPage(page - 1)} title="Previous page">‹</button>
          <span className="pager-info">
            {page * perPage + 1}–{Math.min((page + 1) * perPage, total)} of {total}
          </span>
          <button className="pager-btn" disabled={page >= pages - 1}
            onClick={() => setPage(page + 1)} title="Next page">›</button>
        </span>
      )}
      <select className="pager-size" value={perPage} title="Rows per page"
        onChange={(e) => setPerPage(Number(e.target.value))}>
        {PAGE_SIZES.map((n) => <option key={n} value={n}>{n} / page</option>)}
      </select>
    </div>
  )
}
