import { useEffect, useState } from 'react'
import { call } from '../api'
import ActionButton from './ActionButton'
import ConfirmModal from './ConfirmModal'
import Markdown from './Markdown'
import './UpdateBanner.css'

// Auto-update banner under the topbar. One check per app load (the backend
// caches the GitHub answer); hidden whenever there is nothing to say. Install
// downloads the release zip, swaps the plugin folder (backup kept for
// auto-restore) and then asks for a host restart.
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
  state?: { state?: string; from?: string; to?: string }
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
    return (
      <div className="update-banner err">
        <div className="update-row">
          <span className="update-dot" />
          <span className="update-title">
            {rolledBack
              ? `The update to v${info.state.to} could not start, so v${info.state.from} was restored from its backup.`
              : `The update to v${info.state.to} could not be completed. Check the ${host} console.`}
          </span>
          <span className="update-actions">
            <ActionButton onClick={() => { call('update_ack').catch(() => {}); setHidden(true) }}>
              Got it
            </ActionButton>
          </span>
        </div>
      </div>
    )
  }

  // Installed (this session, or still pending from a previous one): restart note.
  if (installed || info.state?.state === 'pending') {
    const to = installed ? info.latest : info.state?.to
    return (
      <div className="update-banner ok">
        <div className="update-row">
          <span className="update-dot" />
          <span className="update-title">
            Overseer v{to} is installed. Restart {host} to finish the update.
          </span>
        </div>
      </div>
    )
  }

  if (!info.supported || !info.update_available || !info.latest) return null
  if (sessionStorage.getItem(DISMISS_KEY) === info.latest) return null
  const releases = info.releases || []

  return (
    <div className="update-banner">
      <div className="update-row">
        <span className="update-dot" />
        <span className="update-title">
          Overseer v{info.latest} is available
          <span className="update-installed">installed: v{info.current}</span>
        </span>
        <span className="update-actions">
          {releases.length > 0 && (
            <ActionButton onClick={() => setOpen((o) => !o)}>
              {open ? 'Hide notes' : "What's new"}
            </ActionButton>
          )}
          {info.writable ? (
            <ActionButton tone="go" disabled={installing}
              onClick={() => setConfirming(true)}>
              {installing ? 'Installing…' : `Install v${info.latest}`}
            </ActionButton>
          ) : (
            <a className="update-link" target="_blank" rel="noreferrer"
              href={`https://github.com/${info.repo || ''}/releases`}>
              Download from GitHub
            </a>
          )}
          <button className="error-dismiss" title="Skip this version for now"
            onClick={() => { sessionStorage.setItem(DISMISS_KEY, info.latest || ''); setHidden(true) }}>
            ✕
          </button>
        </span>
      </div>
      {!info.writable && (
        <p className="hint-sm">
          The plugin folder is read-only for {host}, so the update cannot install
          itself. Download the zip and replace the folder manually.
        </p>
      )}
      {error && <p className="update-error">{error}</p>}
      {open && (
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
      )}
      {confirming && (
        <ConfirmModal
          title={`Install Overseer v${info.latest}?`}
          message={`Downloads the release from GitHub and replaces the plugin files. Your settings and histories are kept, and the current version is backed up for automatic restore. ${host} needs a restart afterwards.`}
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
