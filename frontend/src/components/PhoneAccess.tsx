import { useEffect, useState } from 'react'
import QRCode from 'qrcode'
import { call } from '../api'
import ActionButton from './ActionButton'

export interface NetInfo {
  lan: boolean            // what the RUNNING server is bound to
  wanted: boolean         // the listen_lan opt-in in config.json
  restart_needed: boolean
  ip: string | null
  port: number
}

// Which of the three cards to show. The server can be LAN-bound (lan:true) yet
// report ip:null when its UDP route probe fails — that is on, but with no
// address to build a QR from, so it is neither the ready "on" state nor the
// "not on yet" setup state.
export type PhoneState = 'on' | 'no-address' | 'setup'

export function phoneState(info: NetInfo, hasQr: boolean): PhoneState {
  if (info.lan && hasQr) return 'on'
  if (info.lan && !info.ip) return 'no-address'
  return 'setup'
}

// "Open on phone": QR code for the UI's LAN URL. The server only listens on
// the network after the listen_lan opt-in AND a C4D restart — until then the
// card walks the user through exactly that. The QR itself lives behind a
// button in a big modal — an always-on code just eats card space.
export default function PhoneAccess() {
  const [info, setInfo] = useState<NetInfo | null>(null)
  const [qr, setQr] = useState('')
  const [err, setErr] = useState('')
  const [open, setOpen] = useState(false)

  const load = () => {
    call('netinfo', {}).then(setInfo).catch((e) => setErr(String(e.message || e)))
  }
  useEffect(load, [])

  const url = info?.ip ? `http://${info.ip}:${info.port}/` : ''
  useEffect(() => {
    if (info?.lan && url) {
      // Rendered at 2x the display size so the modal image stays crisp.
      QRCode.toDataURL(url, { margin: 1, width: 640, color: { dark: '#000000', light: '#ffffff' } })
        .then(setQr).catch((e) => setErr(String(e)))
    }
  }, [info?.lan, url])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open])

  const toggle = (on: boolean) => {
    call('netinfo', { listen_lan: on }).then(setInfo).catch((e) => setErr(String(e.message || e)))
  }

  if (err) return <p className="hint-sm">{err}</p>
  if (!info) return <p className="hint-sm">Checking network status…</p>

  const state = phoneState(info, Boolean(qr))

  return (
    <div className="phone-access">
      {state === 'on' ? (
        <>
          <p className="hint-sm">
            Phone access is on — show the QR code and scan it with your
            phone's camera. Phone and this computer just need to be on the
            same Wi-Fi; the page that opens is this very tool.
          </p>
          <div className="phone-actions">
            <ActionButton tone="go" disabled={false} onClick={() => setOpen(true)}
              title="Show the QR code big — scan it with your phone's camera">
              Show QR code
            </ActionButton>
            <ActionButton disabled={false} onClick={() => toggle(false)}
              title="Make the tool reachable from this computer only again (takes effect after restarting Cinema 4D)">
              Turn phone access off
            </ActionButton>
          </div>
          {open && (
            <div className="confirm-overlay" onClick={() => setOpen(false)}>
              <div className="confirm-box qr-box" role="dialog" aria-modal="true"
                onClick={(e) => e.stopPropagation()}>
                <h3 className="confirm-title">Open on phone</h3>
                <img className="qr-big" src={qr} alt={url} />
                <p className="confirm-msg"><code>{url}</code></p>
                <div className="confirm-actions">
                  <button className="ghost" autoFocus onClick={() => setOpen(false)}>Close</button>
                </div>
              </div>
            </div>
          )}
        </>
      ) : state === 'no-address' ? (
        <>
          <p className="hint-sm">
            Phone access is on, but the LAN address of this computer could not
            be worked out — so there is no QR code to show. Check that this
            computer is connected to your Wi-Fi or network, then check again.
          </p>
          <div className="phone-actions">
            <ActionButton tone="go" disabled={false} onClick={load}
              title="Ask the server again for this computer's network address">
              Check again
            </ActionButton>
            <ActionButton disabled={false} onClick={() => toggle(false)}
              title="Make the tool reachable from this computer only again (takes effect after restarting Cinema 4D)">
              Turn phone access off
            </ActionButton>
          </div>
        </>
      ) : (
        <>
          <p className="hint-sm">
            Get a QR code that opens this tool on your phone — handy for
            reading through your scene away from the desk.
          </p>
          <p className="hint-sm">
            Heads up: while it is on, anyone on the same Wi-Fi could open the
            tool and change your scene. Best used at home or in a network you
            trust, and turned off afterwards.
          </p>
          {info.wanted && !info.lan
            ? <p className="hint-sm"><b>One step left:</b> restart Cinema 4D,
                then come back here — the QR code will be waiting.</p>
            : <ActionButton disabled={false} onClick={() => toggle(true)}
                title="After turning this on, restart Cinema 4D once — then the QR code appears here">
                Turn phone access on
              </ActionButton>}
        </>
      )}
    </div>
  )
}
