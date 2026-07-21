import { useEffect, useState } from 'react'
import { call } from '../api'
import ActionButton from './ActionButton'
import ConfirmModal from './ConfirmModal'
import Markdown from './Markdown'
import './UpdateBanner.css'

// Compact update chip in the topbar (right of the brand, left of the scope
// toggle): top line = the new version, bottom line = What's new / Install / ✕.
// The release notes open in a modal; install confirms first, then downloads,
// swaps the plugin folder (backup kept for auto-restore) and asks for a host
// restart. One check per app load — the backend caches the GitHub answer.
type UpdateRelease = { version: string; name: string; notes: string; date: string }
type UpdateInfo = {
  host?: string
  current?: string
  repo?: string
  supported?: boolean
  latest?: string
  update_available?: boolean
  writable?: boolean
  releases?: UpdateRelease[]
  state?: { state?: string; from?: string; to?: string; reason?: string }
  check_failed?: string
}

const DISMISS_KEY = 'overseer-update-dismissed'

export default function UpdateBanner() {
  const [info, setInfo] = useState<UpdateInfo | null>(null)
  const [open, setOpen] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [installing, setInstalling] = useState(false)
  const [installed, setInstalled] = useState(false)
  const [error, setError] = useState('')
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    let dead = false
    call<UpdateInfo>('update_check')
      .then((res) => { if (!dead) setInfo(res) })
      .catch(() => {})
    return () => { dead = true }
  }, [])

  if (!info || hidden) return null
  const host = info.host || 'the host application'

  // A fresh install failed and the previous version was restored: say so once.
  if (!installed && (info.state?.state === 'rolled_back' || info.state?.state === 'failed')) {
    const rolledBack = info.state.state === 'rolled_back'
    const detail = rolledBack
      ? `The update to v${info.state.to} could not start, so v${info.state.from} was restored from its backup.`
      : `The update to v${info.state.to} could not be completed (${info.state.reason || 'see the host console'}).`
    return (
      <div className="update-banner err" title={detail}>
        <span className="update-line">
          <span className="update-dot" />
          <span className="update-title">Update rolled back</span>
        </span>
        <span className="update-acts">
          {rolledBack && <span className="update-hint">v{info.state.from} restored</span>}
          <ActionButton onClick={() => { call('update_ack').catch(() => {}); setHidden(true) }}>
            Got it
          </ActionButton>
        </span>
      </div>
    )
  }

  // Installed (this session, or still pending from a previous one): restart note.
  if (installed || info.state?.state === 'pending') {
    const to = installed ? info.latest : info.state?.to
    return (
      <div className="update-banner ok">
        <span className="update-line">
          <span className="update-dot" />
          <span className="update-title">v{to} installed</span>
        </span>
        <span className="update-acts">
          <span className="update-hint">restart {host} to finish</span>
        </span>
      </div>
    )
  }

  if (!info.supported || !info.update_available || !info.latest) return null
  if (sessionStorage.getItem(DISMISS_KEY) === info.latest) return null
  const releases = info.releases || []

  return (
    <div className="update-banner">
      <span className="update-line">
        <span className="update-title">v{info.latest} available</span>
        <button className="update-x" title="Skip this version for now"
          onClick={() => { sessionStorage.setItem(DISMISS_KEY, info.latest || ''); setHidden(true) }}>
          ✕
        </button>
      </span>
      <span className="update-acts">
        {releases.length > 0 && (
          <ActionButton onClick={() => setOpen(true)}>What's new</ActionButton>
        )}
        {info.writable ? (
          <ActionButton tone="go" disabled={installing}
            onClick={() => setConfirming(true)}>
            {installing ? 'Installing…' : 'Install'}
          </ActionButton>
        ) : (
          <a className="update-link" target="_blank" rel="noreferrer"
            title={`The plugin folder is read-only for ${host}, so the update cannot install itself. Download the zip and replace the folder manually.`}
            href={`https://github.com/${info.repo || ''}/releases`}>
            Download from GitHub
          </a>
        )}
        {error && <span className="update-error" title={error}>install failed</span>}
      </span>
      {open && (
        <div className="confirm-overlay" onClick={() => setOpen(false)}>
          <div className="confirm-box update-notes-box" role="dialog" aria-modal="true"
            onClick={(e) => e.stopPropagation()}>
            <h3 className="confirm-title">What's new in v{info.latest}</h3>
            <p className="update-notes-sub">installed: v{info.current}</p>
            <div className="update-notes">
              {releases.map((r) => (
                <div key={r.version} className="update-note">
                  <div className="section-head sm">
                    <span>v{r.version}</span>
                    {r.date && <span className="update-date">{r.date}</span>}
                  </div>
                  <Markdown source={r.notes || 'No notes for this release.'} />
                </div>
              ))}
            </div>
            <div className="confirm-actions">
              <button className="ghost" onClick={() => setOpen(false)}>Close</button>
              {info.writable && (
                <button className="apply" disabled={installing}
                  onClick={() => { setOpen(false); setConfirming(true) }}>
                  Install v{info.latest}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
      {confirming && (
        <ConfirmModal
          title={`Install Overseer v${info.latest}?`}
          message={`Overseer handles the update by itself: it downloads v${info.latest} from GitHub and installs it in place. Your settings and histories are kept, and the current version is saved as a backup that is restored automatically if the new one fails to start. Afterwards, restart ${host} once to finish.`}
          confirmLabel="Install"
          onCancel={() => setConfirming(false)}
          onConfirm={() => {
            setConfirming(false)
            setInstalling(true)
            setError('')
            call('update_install', { version: info.latest })
              .then(() => setInstalled(true))
              .catch((ex) => setError(ex instanceof Error ? ex.message : String(ex)))
              .finally(() => setInstalling(false))
          }}
        />
      )}
    </div>
  )
}
