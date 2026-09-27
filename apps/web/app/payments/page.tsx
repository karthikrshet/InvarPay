'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
import { Sidebar } from '../../components/Sidebar'

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{status}</span>
}

function formatAmount(amount: number, currency: string) {
  return `${currency} ${(amount / 100).toFixed(2)}`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
  })
}

export default function PaymentsPage() {
  const [payments, setPayments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Fetch payments via API (requires auth in production)
    // For demo: shows empty state with guidance
    setLoading(false)
  }, [])

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div className="flex items-center justify-between">
            <div>
              <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.3 }}>
                Payment Attempts
              </h1>
              <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
                All payment attempts with state machine timeline · Reconciliation status
              </p>
            </div>
          </div>
        </div>
        <div className="page-body">
          <div className="alert alert-info" style={{ marginBottom: 24 }}>
            🔑 Authenticate with <code className="mono">X-API-Key: pg_test_...</code> to load payment data.
            Run <code className="mono">make demo</code> to seed synthetic payments.
          </div>

          {/* State invariant reminder */}
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header"><div className="card-title">Payment State Machine Invariants</div></div>
            <div className="card-body">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                <div className="alert alert-warning" style={{ fontSize: 12 }}>
                  ⚠️ <strong>unknown ≠ failed</strong><br/>
                  An ambiguous outcome is NOT a failure. Reconcile before any action.
                </div>
                <div className="alert alert-danger" style={{ fontSize: 12 }}>
                  🚫 <strong>No retry on unknown</strong><br/>
                  Network timeouts → unknown state → reconcile first. Never auto-retry.
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header" style={{ padding: '20px 24px' }}>
              <div className="card-title">Recent Payments</div>
              <div className="flex gap-2">
                {['captured', 'unknown', 'failed', 'pending'].map(s => (
                  <StatusBadge key={s} status={s} />
                ))}
              </div>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              {payments.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">₹</div>
                  <div className="empty-title">No payments yet</div>
                  <div className="empty-desc">
                    Run <code className="mono" style={{ fontSize: 11 }}>make demo</code> to generate synthetic payment data,
                    or use the API to create real test payments via Razorpay test mode.
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    <a href="http://localhost:8000/docs#/Payments" target="_blank" className="btn btn-secondary" style={{ fontSize: 12 }}>
                      API Reference ↗
                    </a>
                  </div>
                </div>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Payment ID</th>
                      <th>Status</th>
                      <th>Amount</th>
                      <th>Provider ID</th>
                      <th>Reconciled</th>
                      <th>Created</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map(p => (
                      <tr key={p.id}>
                        <td><span className="id-chip">{p.id}</span></td>
                        <td><StatusBadge status={p.status} /></td>
                        <td style={{ fontFamily: 'monospace' }}>{formatAmount(p.amount, p.currency)}</td>
                        <td><span className="id-chip">{p.provider_payment_id || '—'}</span></td>
                        <td>{p.is_reconciled ? '✓' : '—'}</td>
                        <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{formatDate(p.created_at)}</td>
                        <td>
                          <Link href={`/payments/${p.id}`} className="btn btn-ghost" style={{ fontSize: 11, padding: '5px 10px' }}>
                            Timeline →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
