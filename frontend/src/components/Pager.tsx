import { useState } from 'react'

export const PAGE_SIZE = 25

export interface PagerState {
  page: number
  pages: number
  setPage: (p: number) => void
  total: number
  perPage: number
}

// Shared pagination for every preview/list: 25 rows per page, prev/next.
// The page index self-clamps when the list shrinks (apply/filter), so no
// reset effects are needed at the call sites.
export function usePager<T>(items: T[], perPage: number = PAGE_SIZE):
    PagerState & { rows: T[] } {
  const [rawPage, setPage] = useState(0)
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
