import { describe, expect, it } from 'vitest'
import { phoneState, type NetInfo } from './PhoneAccess'

const base: NetInfo = { lan: false, wanted: false, restart_needed: false, ip: null, port: 8787 }

describe('phoneState', () => {
  it('is on when LAN-bound and a QR code is ready', () => {
    expect(phoneState({ ...base, lan: true, ip: '192.168.0.5' }, true)).toBe('on')
  })

  it('is no-address when LAN-bound but the IP probe returned null', () => {
    expect(phoneState({ ...base, lan: true, ip: null }, false)).toBe('no-address')
  })

  it('stays no-address (not setup) even when opt-in is set', () => {
    expect(phoneState({ ...base, lan: true, wanted: true, ip: null }, false)).toBe('no-address')
  })

  it('is setup when not LAN-bound', () => {
    expect(phoneState({ ...base, lan: false, wanted: true }, false)).toBe('setup')
  })
})
