'use client'

import { useEffect, useState } from 'react'
import { Sidebar } from '../../components/Sidebar'

interface Investigation {
  id: string
  payment_id: string
  status: string
  finding: string
  risk_level: string
  requires_approval: boolean
  created_at: string
}

export default function InvestigationsPage() {
  const [investigations, setInvestigations] = useState<Investigation[]>([])

  useEffect(() => {
    setInvestigations([
      {
        id: 'inv_01HZX9901',
        payment_id: 'pay_01HZX87654ABCD1234567890',
        status: 'completed',
        finding: 'Deterministic matching verified. Webhook signature valid. No double charge risk.',
        risk_level: 'LOW',
        requires_approval: false,
        created_at: new Date().toISOString(),
      },
      {
        id: 'inv_01HZX9902',
        payment_id: 'pay_01HZX87654ABCD1234567899',
        status: 'awaiting_approval',
        finding: 'Provider returned timeout (unknown outcome). Automatic retry blocked by policy. Manual reconciliation recommended.',
        risk_level: 'HIGH',
        requires_approval: true,
        created_at: new Date(Date.now() - 1800000).toISOString(),
      },
    ])
  }, [])

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Payment Investigations</h1>
            <p className="page-subtitle">LangGraph AI Agent incident reports & safe recovery proposals</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>POLICY ENFORCED (DENY-BY-DEFAULT)</span>
          </div>
        </header>

        <div style={{ display: 'grid', gap: 16 }}>
          {investigations.map(inv => (
            <div key={inv.id} className="card" style={{ borderLeft: inv.requires_approval ? '4px solid #f59e0b' : '4px solid #10b981' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div>
                  <span style={{ fontWeight: 600, fontSize: 16 }}>Investigation {inv.id}</span>
                  <span style={{ marginLeft: 12, color: 'var(--color-text-muted)', fontSize: 13 }}>
                    Target: <code>{inv.payment_id}</code>
                  </span>
                </div>
                <div>
                  <span className={`badge badge-${inv.risk_level === 'HIGH' ? 'unknown' : 'captured'}`}>
                    Risk: {inv.risk_level}
                  </span>
                  {inv.requires_approval && (
                    <span className="badge badge-pending" style={{ marginLeft: 8 }}>
                      REQUIRES APPROVAL
                    </span>
                  )}
                </div>
              </div>

              <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6, marginBottom: 16 }}>
                {inv.finding}
              </p>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 12, borderTop: '1px solid var(--color-border)' }}>
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                  Generated at {new Date(inv.created_at).toLocaleTimeString()} · Read-only tool boundary
                </span>
                {inv.requires_approval && (
                  <button className="btn btn-primary" style={{ padding: '6px 14px', fontSize: 13 }}>
                    Review & Approve Recovery
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
