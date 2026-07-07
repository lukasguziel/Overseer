// Pure helpers for the RuleV2 cards: plain-language labels, defaults and
// the category list. No React here so it stays unit-testable.
import type { Category, MatchJson, RuleType, RuleV2 } from '../types'

export const RULE_CATEGORIES: Category[] = ['light', 'camera', 'null', 'mesh', 'spline', 'other']

export const RULE_TYPE_LABELS: Record<RuleType, string> = {
  prefix: 'Prefix',
  renumber: 'Nummerierung',
  condition: 'Wenn/Dann',
  layer: 'Layer',
}

// German phrase describing which objects a match selects (UI copy).
export function matchLabel(m?: MatchJson): string {
  if (!m) return 'alle Objekte'
  const parts: string[] = []
  if (m.categories?.length) parts.push(m.categories.join(', '))
  if (m.keywords?.length) parts.push('Namen mit ' + m.keywords.map((k) => `„${k}“`).join('/'))
  if (m.types?.length) parts.push('Typ ' + m.types.join('/'))
  if (m.name_regex) parts.push(`Regex /${m.name_regex}/`)
  let s = parts.length ? parts.join(', ') : 'alle Objekte'
  if (m.under_group) s += ` unter „${m.under_group}“`
  return s
}

// One-line plain-language summary of a rule for the card header.
export function ruleLabel(r: RuleV2): string {
  switch (r.type) {
    case 'prefix':
      return `Prefix „${r.prefix}“ für ${matchLabel(r.match)}`
    case 'renumber':
      return `Nummerierung: Lücken schließen, Padding ${r.pad}`
        + (r.per_parent ? ', pro Elternobjekt' : '')
        + ` (${matchLabel(r.match)})`
    case 'condition': {
      const conds: string[] = []
      if (r.when.duplicates_gt != null) conds.push(`Duplikate > ${r.when.duplicates_gt}`)
      if (r.when.match) conds.push(matchLabel(r.when.match))
      const acts: string[] = []
      if (r.then.suffix_scheme) acts.push(r.then.suffix_scheme === 'alpha' ? 'Suffix A/B/C' : 'Suffix 1/2/3')
      if (r.then.apply_prefix) acts.push(`Prefix „${r.then.apply_prefix}“`)
      if (r.then.assign_layer) acts.push(`Layer „${r.then.assign_layer}“`)
      return `Wenn ${conds.join(' & ') || 'immer'} → ${acts.join(', ') || '(keine Aktion)'}`
    }
    case 'layer':
      return `Layer „${r.layer}“ für ${matchLabel(r.match)}`
  }
}

let counter = 0
export function newRuleId(): string {
  counter += 1
  return `r${Date.now().toString(36)}${counter}`
}

// Fresh rule of the given type with sensible defaults.
export function newRule(type: RuleType): RuleV2 {
  const base = { id: newRuleId(), enabled: true, priority: 50 }
  switch (type) {
    case 'prefix': return { ...base, type, prefix: 'PFX_', match: {} }
    case 'renumber': return { ...base, type, match: {}, pad: 2, start: 1, per_parent: true }
    case 'condition': return { ...base, type, when: {}, then: {} }
    case 'layer': return { ...base, type, layer: 'Layer', match: {} }
  }
}
