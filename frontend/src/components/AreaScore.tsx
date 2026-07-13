import Ring from './Ring'
import { scoreTone } from '../lib/score'

// The area's health/progress ring — sits at the right edge of a tab's opening
// SectionIntro (via its `aside` slot). Renders nothing while there is no score.
export default function AreaScore({ score }: { score: number | null }) {
  if (score == null) return null
  return (
    <div className="area-score"
      title="How far this area is worked through — applied fixes and accepted-as-is both count. Reach 100% by deciding on every item.">
      <Ring pct={score} tone={scoreTone(score)} />
    </div>
  )
}
