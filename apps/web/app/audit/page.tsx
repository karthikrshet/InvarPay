'use client'

import { useEffect, useState } from 'react'
import { Sidebar } from '../../components/Sidebar'

interface AuditEvent {
  id: string
  action: string
  actor: string
  resource_type: string
  resource_id: string
  hash: string
  timestamp: string
}

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([])

  useEffect(() => {
    setEvents([
      {
        id: 'aud_01HZX771',
        action: 'PAYMENT_CAPTURE_VERIFIED',
        actor: 'webhook:razorpay-test',
        resource_type: 'payment_attempt',
        resource_id: 'pay_01HZX87654ABCD1234567890',
        hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        timestamp: new Date().toISOString(),
      },
      {
        id: 'aud_01HZX772',
        action: 'WEBHOOK_SIGNATURE_VALIDATED',
        actor: 'security:hmac-sha256',
        resource_type: 'provider_event',
        resource_id: 'evt_01HZX229',
        hash: 'ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb',
        timestamp: new Date(Date.now() - 300000).toISOString(),
      },
      {
        id: 'aud_01HZX773',
        action: 'RETRY_PREVENTED_AMBIGUOUS_STATE',
        actor: 'state_machine:guard',
        resource_type: 'payment_attempt',
        resource_id: 'pay_01HZX87654ABCD1234567899',
        hash: '4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce',
        timestamp: new Date(Date.now() - 900000).toISOString(),
      },
    ])
  }, [])

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Audit Trail</h1>
            <p className="page-subtitle">Append-only, SHA-256 hash-chained financial mutation ledger</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>TAMPER-EVIDENT INTEGRITY</span>
          </div>
        </header>

        <div className="card">
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Audit ID</th>
                  <th>Action</th>
                  <th>Actor</th>
                  <th>Resource</th>
                  <th>Cryptographic Hash</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {events.map(ev => (
                  <tr key={ev.id}>
                    <td><code>{ev.id}</code></td>
                    <td>
                      <span className="badge badge-initiated">{ev.action}</span>
                    </td>
                    <td>{ev.actor}</td>
                    <td>{ev.resource_type}: <code>{ev.resource_id.slice(0, 12)}...</code></td>
                    <td>
                      <code style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                        {ev.hash.slice(0, 18)}...
                      </code>
                    </td>
                    <td style={{ color: 'var(--color-text-muted)' }}>
                      {new Date(ev.timestamp).toLocaleTimeString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
