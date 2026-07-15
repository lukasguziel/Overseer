// Material & texture actions of the Materials tab (and the texture tables),
// extracted from useOrganizer: every action is one fire() call — optimistic
// status, outcome message, standard follow-up. useOrganizer spreads the
// returned callbacks into the org object, so consumers are unchanged.
import { useCallback } from 'react'
import { call } from '../api'
import { plural } from '../lib/format'

// One fire-and-forget action: progress status while the call runs, the
// outcome (or the error) after, then the standard follow-up — a debounced
// background refresh or a full re-analysis.
export interface FireOpts<R = any> {
  start: string                     // status while the call runs ("Deleting X…")
  op: string                        // API op for call()
  args?: unknown
  ok: (r: R) => string              // outcome message from the response
  fail: string                      // verb shown as "<fail> ✗" on error
  pin?: boolean                     // outcome via note() — survives the follow-up analysis
  after?: 'analyze' | 'refresh' | number  // number = refreshSoon(delay)
  skipAfter?: (r: R) => boolean     // e.g. a cancelled file picker: no refresh
  onFail?: () => void               // extra recovery (reload the affected plan)
}
export type FireFn = <R = any>(o: FireOpts<R>) => void
export type RunFn = <T>(label: string, fn: () => Promise<T>) => Promise<T | undefined>

export function useTextureActions(ctx: {
  fire: FireFn
  run: RunFn
  note: (msg: string) => void
  doAnalyze: () => Promise<unknown> | void
  includeHidden: boolean
}) {
  const { fire, run, note, doAnalyze, includeHidden } = ctx

  // Select a material in the C4D material manager and frame the first object
  // that carries it (used by the texture tables).
  const doFocusMaterial = useCallback((name: string) => fire({
    start: `Focusing material “${name}”…`,
    op: 'focus_material', args: { name },
    ok: (r) => r.object
      ? `Selected “${name}” · framed “${r.object}” ✓`
      : r.ok ? `Selected “${name}” (assigned to no object)` : 'Material not found',
    fail: 'Focus',
  }), [fire])

  const doDeleteMaterial = useCallback((name: string) => fire({
    start: `Deleting ${name}…`,
    op: 'delete_material', args: { name, include_hidden: includeHidden },
    ok: (r) => r.deleted ? `Deleted material “${name}” ✓ (undoable)` : `“${name}” is in use — kept`,
    fail: 'Delete', after: 'analyze',
  }), [fire, includeHidden])

  const doDeleteAllUnused = useCallback((count: number) => fire({
    start: `Deleting ${plural(count, 'unused material')}…`,
    op: 'delete_unused_materials', args: { include_hidden: includeHidden },
    ok: (r) => `Deleted ${plural(r.deleted, 'unused material')} ✓ (undoable)`,
    fail: 'Delete', after: 'analyze',
  }), [fire, includeHidden])

  const doFixTexturesRelative = useCallback((materials?: string[]) => fire({
    start: 'Making texture paths relative…',
    op: 'fix_textures_relative', args: materials ? { materials } : {},
    ok: (r) => r.fixed
      ? `Rewrote ${plural(r.fixed, 'texture path')} to relative ✓ (undoable)`
      : 'No relocatable absolute textures to fix.',
    fail: 'Fix', after: 'analyze',
  }), [fire])

  // Copy out-of-project textures into <project>/<subdir> and relink the
  // shaders relatively. The copy itself is a file operation (not undoable),
  // the relink is one undo step — the confirm dialog says so.
  const doCollectTextures = useCallback((subdir: string, paths?: string[]) => fire({
    start: `Copying textures into “${subdir}”…`,
    op: 'collect_textures', args: paths ? { subdir, paths } : { subdir },
    ok: (r) => {
      // "Nothing happened" is never an acceptable answer: the server reports
      // per reference WHY it was not collected (file gone, already inside the
      // project, copy failed, no parameter held the path) — show that.
      const why: string[] = [...new Set((r.diag || []) as string[])]
      return r.relinked
        ? `Copied ${plural(r.copied, 'file')} → ${subdir}/ · relinked ${plural(r.relinked, 'reference')} ✓ (relink undoable)`
          + (r.skipped ? ` · ${r.skipped} skipped${why.length ? `: ${why.join(' · ')}` : ''}` : '')
        : why.length
          ? `Nothing collected — ${why.join(' · ')}`
          : 'No out-of-project textures to collect.'
    },
    fail: 'Collect', pin: true, after: 'analyze',
  }), [fire])

  // Relink missing textures by searching a folder recursively for the file
  // names; matches are rewritten (project-relative when possible).
  const doRelinkTextures = useCallback((folder: string) => fire({
    start: `Searching “${folder}” for missing textures…`,
    op: 'relink_textures', args: { folder },
    ok: (r) => `Relinked ${plural(r.relinked, 'texture')} ✓ (undoable)`
      + (r.not_found ? ` · ${r.not_found} not found there` : '')
      + (r.skipped ? ` · ${r.skipped} skipped` : ''),
    fail: 'Relink', after: 'analyze',
  }), [fire])

  // Per-row texture reference edit: rewrite (or blank) ONE reference,
  // identified by its current raw path + owning material.
  const doSetTexturePath = useCallback((path: string, newPath: string, material?: string) => fire({
    start: newPath ? 'Rewriting texture reference…' : 'Clearing texture reference…',
    op: 'set_texture_path', args: { path, new_path: newPath, material },
    ok: () => newPath ? `Reference → “${newPath}” ✓ (undoable)` : 'Reference cleared ✓ (undoable)',
    fail: 'Edit', after: 300,
  }), [fire])

  // Pick a replacement file for ONE reference via C4D's native file dialog
  // (the request waits while the dialog is open inside Cinema 4D).
  const doPickTexturePath = useCallback((path: string, material?: string) => fire({
    start: 'Pick the file in the Cinema 4D window…',
    op: 'pick_texture_path', args: { path, material },
    ok: (r) => r.cancelled ? 'File picker cancelled.' : `Reference → “${r.picked}” ✓ (undoable)`,
    skipAfter: (r) => !!r.cancelled,
    fail: 'Pick', after: 300,
  }), [fire])

  // Batch-resize textures to a percentage: writes resized COPIES next to the
  // originals (suffix _25/_50/_75) and relinks the shaders (undoable, journaled).
  const doTextureResize = useCallback((paths: string[], percent: number) => fire({
    start: `Resizing ${plural(paths.length, 'texture')} to ${percent}%…`,
    op: 'texture_resize', args: { paths, percent },
    ok: (r) => {
      // A skip is a non-event to the user unless they learn WHY — the
      // backend gives a reason per file, so surface it instead of a count.
      const why: string[] = [...new Set((r.results || [])
        .filter((x: { status: string }) => x.status === 'skipped')
        .map((x: { note: string }) => x.note)
        .filter(Boolean) as string[])]
      return !r.resized
        ? `Nothing resized${why.length ? ` — ${why.join(' · ')}` : ''}`
        : `Resized ${plural(r.resized, 'texture')} to ${percent}% ✓ (undoable)`
          + (r.skipped ? ` · ${r.skipped} skipped: ${why.join(' · ')}` : '')
    },
    fail: 'Resize', pin: true, after: 'analyze',
  }), [fire])

  // Convert texture paths between relative and absolute form (undoable,
  // journaled). Wrapped in run(): the follow-up analysis then nests (busy
  // depth 2) and leaves the pinned outcome alone — outside run() the analysis
  // would overwrite the message with "Analysis ✓".
  const doTextureRepath = useCallback((paths: string[], mode: 'relative' | 'absolute') =>
    run(`Making ${plural(paths.length, 'path')} ${mode}`, async () => {
      const r = await call('texture_repath', { paths, mode })
      // "Nothing happened" is never an acceptable answer: the server reports
      // per path WHY it could not rewrite it (file gone, already relative,
      // outside the project, no parameter held the path) — show that.
      const why: string[] = (r.diag || []) as string[]
      note(r.changed
        ? `Rewrote ${plural(r.changed, 'path')} to ${mode} ✓ (undoable)`
        : why.length
          ? `Nothing rewritten — ${why.join(' · ')}`
          : `No paths to make ${mode}.`)
      await doAnalyze()
    }),
  [run, note, doAnalyze])

  // Clear dead references: blank the path on shaders whose file is missing.
  const doClearMissingTextures = useCallback(() => fire({
    start: 'Clearing missing texture references…',
    op: 'clear_missing_textures',
    ok: (r) => `Cleared ${plural(r.cleared, 'missing reference')} ✓ (undoable)`
      + (r.skipped ? ` · ${r.skipped} skipped (parameter not writable)` : ''),
    fail: 'Clear', after: 'analyze',
  }), [fire])

  return {
    doFocusMaterial, doDeleteMaterial, doDeleteAllUnused, doFixTexturesRelative,
    doCollectTextures, doRelinkTextures, doSetTexturePath, doPickTexturePath,
    doTextureResize, doTextureRepath, doClearMissingTextures,
  }
}
