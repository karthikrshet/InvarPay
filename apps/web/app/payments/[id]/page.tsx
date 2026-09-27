'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Sidebar } from '../../../components/Sidebar'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${(status || 'unknown').toLowerCase()}`}>{status}</span>
}

function formatAmount(amount: number, currency: string) {
  return `${currency} ${(amount / 100).toFixed(2)}`
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  })
}

interface TimelineEvent {
  time: string
  title: string
  detail: string
  type: string
}

function buildTimeline(payment: any): TimelineEvent[] {
  const events: TimelineEvent[] = []

  if (payment.created_at) {
    events.push({
      time: formatDate(payment.created_at),
      title: 'Payment Attempt Created',
      detail: `ID: ${payment.id} · Idempotency key set`,
      type: 'created'
    })
  }
  if (payment.initiated_at) {
    events.push({
      time: formatDate(payment.initiated_at),
      title: 'Payment Initiated',
      detail: 'Request sent to provider',
      type: 'initiated'
    })
  }
  if (payment.authorized_at) {
    events.push({
      time: formatDate(payment.authorized_at),
      title: 'Payment Authorized',
      detail: `Provider: ${payment.provider_payment_id || 'unknown'}`,
      type: 'authorized'
    })
  }
  if (payment.captured_at) {
    events.push({
      time: formatDate(payment.captured_at),
      title: 'Payment Captured ✓',
      detail: formatAmount(payment.amount ?? 0, payment.currency ?? 'INR'),
      type: 'captured'
    })
  }
  if (payment.failed_at) {
    events.push({
      time: formatDate(payment.failed_at),
      title: 'Payment Failed',
      detail: payment.failure_reason || payment.failure_code || 'No details',
      type: 'failed'
    })
  }
  if (payment.status === 'unknown') {
    events.push({
      time: 'Now',
      title: '⚠️ Outcome Unknown',
      detail: 'Network timeout or provider error. Do NOT retry. Reconcile first to determine outcome.',
      type: 'unknown'
    })
  }
  if (payment.reconciled_at) {
    events.push({
      time: formatDate(payment.reconciled_at),
      title: 'Reconciliation Completed',
      detail: 'Reconciled against provider data',
      type: 'captured'
    })
  }

  // Add provider events
  for (const evt of (payment.provider_events || [])) {
    events.push({
      time: formatDate(evt.received_at),
      title: `Webhook: ${evt.event_type}`,
      detail: `Provider: ${evt.provider} · Sig verified: ${evt.signature_verified ? '✓' : '✗'} · Deduped: ${evt.processed ? 'processed' : 'pending'}`,
      type: evt.signature_verified ? 'authorized' : 'failed',
    })
  }

  return events.sort((a, b) => a.time.localeCompare(b.time))
}

export default function PaymentDetailPage() {
  const params = useParams()
  const paymentId = (params?.id as string) || ''
  const [payment, setPayment] = useState<any | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!paymentId) {
      setLoading(false)
      return
    }
    const apiKey = typeof window !== 'undefined' ? localStorage.getItem('pg_api_key') || '' : ''
    fetch(`${API_URL}/v1/payments/${paymentId}`, {
      headers: { 'X-API-Key': apiKey }
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => { setPayment(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [paymentId])

  const handleReconcile = async () => {
    const apiKey = typeof window !== 'undefined' ? localStorage.getItem('pg_api_key') || '' : ''
    try {
      await fetch(`${API_URL}/v1/payments/${paymentId}/reconcile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({}),
      })
      if (typeof window !== 'undefined') {
        window.location.reload()
      }
    } catch (err) {
      console.error('Reconciliation failed:', err)
    }
  }

  const handleInvestigate = async () => {
    const apiKey = typeof window !== 'undefined' ? localStorage.getItem('pg_api_key') || '' : ''
    try {
      await fetch(`${API_URL}/v1/payments/${paymentId}/investigations`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
        body: JSON.stringify({ trigger_reason: 'Requested from dashboard' }),
      })
      if (typeof window !== 'undefined') {
        alert('Investigation started. Check Investigations tab.')
      }
    } catch (err) {
      console.error('Investigation failed:', err)
    }
  }

  const timeline = payment ? buildTimeline(payment) : []

  const paymentDetails = payment ? [
    { label: 'Amount', value: formatAmount(payment.amount ?? 0, payment.currency ?? 'INR') },
    { label: 'Status', value: null },
    { label: 'Provider ID', value: payment.provider_payment_id || '—' },
    { label: 'Provider Status', value: payment.provider_status || '—' },
    { label: 'Reconciled', value: payment.is_reconciled ? '✓ Yes' : '✗ No' },
    { label: 'Order ID', value: payment.order_id || '—' },
  ] : []

  return (
    <div className="layout">
      <Sidebar />

      <main className="main-content">
        <div className="page-header">
          <div className="flex items-center gap-3">
            <Link href="/payments" className="btn btn-ghost" style={{ fontSize: 12, padding: '6px 12px' }}>
              ← Back
            </Link>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 700 }}>
                Payment Timeline
              </h1>
              <span className="id-chip" style={{ marginTop: 4, display: 'inline-block' }}>{paymentId}</span>
            </div>
            {payment && <StatusBadge status={payment.status} />}
          </div>
        </div>

        <div className="page-body">
          {loading ? (
            <div className="alert alert-info">⟳ Loading payment data...</div>
          ) : !payment ? (
            <div className="card">
              <div className="empty-state">
                <div className="empty-icon">₹</div>
                <div className="empty-title">Payment not found</div>
                <div className="empty-desc">
                  This payment ID does not exist or you don&apos;t have access to it.
                  Authenticate with a valid API key to load payment data.
                </div>
              </div>
            </div>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>
              {/* Timeline */}
              <div>
                <div className="card">
                  <div className="card-header"><div className="card-title">Event Timeline</div></div>
                  <div className="card-body">
                    {payment.status === 'unknown' && (
                      <div className="alert alert-warning" style={{ marginBottom: 20, fontSize: 12 }}>
                        ⚠️ <strong>Unknown outcome detected.</strong> This payment may or may not have been captured.
                        Do NOT retry. Use Reconcile to determine the actual status.
                      </div>
                    )}
                    <div className="timeline">
                      {timeline.map((event, i) => (
                        <div key={i} className="timeline-item">
                          <div className={`timeline-dot ${event.type}`} />
                          <div className="timeline-time">{event.time}</div>
                          <div className="timeline-title">{event.title}</div>
                          <div className="timeline-detail">{event.detail}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Sidebar details */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                <div className="card">
                  <div className="card-header"><div className="card-title">Payment Details</div></div>
                  <div className="card-body">
                    {paymentDetails.map(({ label, value }) => (
                      <div key={label} style={{
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        padding: '8px 0', borderBottom: '1px solid rgba(255,255,255,0.04)',
                        fontSize: 13
                      }}>
                        <span style={{ color: 'var(--text-muted)' }}>{label}</span>
                        {label === 'Status' ? (
                          <StatusBadge status={payment.status} />
                        ) : (
                          <span className="mono">{value}</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <div className="card-header"><div className="card-title">Actions</div></div>
                  <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <button
                      className="btn btn-primary"
                      style={{ width: '100%', justifyContent: 'center' }}
                      onClick={handleReconcile}
                    >
                      ⟳ Reconcile Payment
                    </button>
                    <button
                      className="btn btn-secondary"
                      style={{ width: '100%', justifyContent: 'center' }}
                      onClick={handleInvestigate}
                    >
                      🔍 Start Investigation
                    </button>
                    {payment.status === 'unknown' && (
                      <div className="alert alert-warning" style={{ fontSize: 11, marginTop: 4 }}>
                        🚫 Retry disabled for unknown-outcome payments. Reconcile first.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
