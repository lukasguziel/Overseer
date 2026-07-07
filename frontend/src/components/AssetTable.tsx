import type { SceneNode } from '../types'
import { catColor } from '../lib/colors'
import { humanNum } from '../lib/format'
import type { FocusFn } from './Treemap'

// Kompakte, klickbare Objekt-Tabelle (gleicher Stil wie der Assets-Tab).
export default function AssetTable({ rows, onFocus, empty }: {
  rows: SceneNode[]
  onFocus?: FocusFn
  empty?: string
}) {
  if (!rows.length) return <div className="fl-empty">{empty || 'None.'}</div>
  return (
    <div className="asset-table-wrap flat">
      <table className="asset-table"><tbody>
        {rows.map((n, i) => (
          <tr key={n.guid ?? i} className="asset-row" onClick={() => onFocus?.(n.guid, n.name)}
            title="Select & frame in viewport">
            <td className="l">
              {n.category && <span className="cat-dot" style={{ background: catColor(n.category) }} />}
              {n.name}
            </td>
            <td className="dim">{n.type}</td>
            <td className="r">{humanNum(n.polygons)}</td>
          </tr>
        ))}
      </tbody></table>
    </div>
  )
}
