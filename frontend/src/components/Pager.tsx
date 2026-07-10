import { useRef, useState } from 'react'

export const PAGE_SIZE = 25

export interface PagerState {
  page: number
  pages: number
  setPage: (p: number) => void
  total: number
  perPage: number
}

// Shared pagination for every preview/list: 25 rows per page, prev/next.
// The page index self-clamps when the list shrinks (apply/filter). Lists
// with user filters additionally pass a `resetKey` (the filter state, e.g.
// joined into a string): whenever it changes the pager jumps back to page 1
// — staying on page 3 of a freshly filtered list is never what you want.
export function usePager<T>(items: T[], perPage: number = PAGE_SIZE, resetKey?: unknown):
    PagerState & { rows: T[] } {
  const [rawPage, setPage] = useState(0)
  const lastKey = useRef(resetKey)
  if (!Object.is(lastKey.current, resetKey)) {
    // Render-phase state adjustment (the React-sanctioned pattern for
    // "reset state when an input changes").
    lastKey.current = resetKey
    if (rawPage !== 0) setPage(0)
  }
  const pages = Math.max(1, Math.ceil(items.length / perPage))
  const page = Math.min(rawPage, pages - 1)
  return {
    rows: items.slice(page * perPage, (page + 1) * perPage),
    page, pages, setPage, total: items.length, perPage,
  }
}

export default function Pager({ pager }: { pager: PagerState }) {
  const { page, pages, setPage, total, perPage } = pager
  if (pages <= 1) return null
  return (
    <div className="pager">
      <button className="pager-btn" disabled={page === 0}
        onClick={() => setPage(page - 1)} title="Previous page">‹</button>
      <span className="pager-info">
        {page * perPage + 1}–{Math.min((page + 1) * perPage, total)} of {total}
      </span>
      <button className="pager-btn" disabled={page >= pages - 1}
        onClick={() => setPage(page + 1)} title="Next page">›</button>
    </div>
  )
}
