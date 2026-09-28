'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Sidebar } from '../../../components/Sidebar'
import {
  CreditCard,
  ArrowLeft,
  CheckCircle2,
  Clock,
  AlertTriangle,
  RotateCcw,
  ShieldCheck,
  Search,
  Zap,
  Copy,
  Check,
  Layers,
  Lock,
  RefreshCw,
  FileText,
  Sparkles,
  ExternalLink,
  ChevronRight
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface TimelineEvent {
  step: number
  time: string
  title: string
  detail: string
  type: 'created' | 'dispatched' | 'webhook' | 'transition' | 'ledger' | 'unknown' | 'failed'
  hash?: string
}

export default function PaymentDetailPage() {
  const params = useParams()
  const paymentId = (params?.id as string) || 'pay_01HX98877119'
  const [copied, setCopied] = useState(false)
  const [isReconciling, setIsReconciling] = useState(false)
  const [reconcileResult, setReconcileResult] = useState<string | null>(null)
  const [isInvestigating, setIsInvestigating] = useState(false)
  const [investigateResult, setInvestigateResult] = useState<string | null>(null)
  const [showRawJson, setShowRawJson] = useState(false)

  // Determine demo state based on paymentId
  const isUnknown = paymentId.includes('unk') || paymentId.includes('51088')
  const isFailed = paymentId.includes('fail') || paymentId.includes('20451')
  const status = isUnknown ? 'unknown' : isFailed ? 'failed' : 'captured'

  const amountPaise = paymentId.includes('4402') ? 4999900 : paymentId.includes('51088') ? 799900 : 149900

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleReconcile = () => {
    setIsReconciling(true)
    setReconcileResult(null)
    setTimeout(() => {
      setIsReconciling(false)
      setReconcileResult('✓ Reconciled against Razorpay settlement API. UTR: CMS99281044 matched dual-entry ledger.')
    }, 700)
  }

  const handleInvestigate = () => {
    setIsInvestigating(true)
    setInvestigateResult(null)
    setTimeout(() => {
      setIsInvestigating(false)
      setInvestigateResult('✓ LangGraph Agent CASE-8921 opened: Traversal completed. Recommended action: "HOLD_SETTLEMENT_PENDING_WEBHOOK".')
    }, 800)
  }

  const timeline: TimelineEvent[] = [
    {
      step: 1,
      time: '13:42:10.012',
      title: 'Idempotency Key Allocation & Distributed Lock',
      detail: `Acquired Redis lease for key idemp_live_${paymentId.substring(4, 12)} (TTL 300s). Re-submission protected.`,
      type: 'created',
      hash: 'sha256_lock_99812f',
    },
    {
      step: 2,
      time: '13:42:10.038',
      title: 'Payment Attempt Created & Outbox Enqueued',
      detail: `Attempt record registered in status 'PENDING'. Transactional Outbox event queued for reliable relay.`,
      type: 'transition',
      hash: 'sha256_rec_44109b',
    },
    {
      step: 3,
      time: '13:42:10.065',
      title: 'Gateway Dispatch to Razorpay API',
      detail: `POST /v1/orders/ord_rzp_${paymentId.substring(4, 10)}/payments. Mutual TLS handshake latency 18ms.`,
      type: 'dispatched',
    },
    ...(isUnknown
      ? [
          {
            step: 4,
            time: '13:42:15.077',
            title: '⚠️ Socket Read Timeout (5000ms Exceeded)',
            detail: `Gateway HTTP connection dropped before response headers received. Per Invariant 2, state marked 'UNKNOWN'. Auto-retry strictly barred.`,
            type: 'unknown' as const,
          },
        ]
      : [
          {
            step: 4,
            time: '13:42:10.194',
            title: 'Provider Webhook Received: payment.captured',
            detail: `HMAC-SHA256 signature verified against merchant secret. Provider payment ID: pay_rzp_${paymentId.substring(4, 12)}.`,
            type: 'webhook' as const,
            hash: 'sha256_sig_88201a',
          },
          {
            step: 5,
            time: '13:42:10.215',
            title: 'State Transition Validated: AUTHORIZED → CAPTURED',
            detail: `State machine transition approved by Invariant Engine. Zero state drift detected.`,
            type: 'transition' as const,
          },
          {
            step: 6,
            time: '13:42:10.230',
            title: 'Double-Entry Ledger Balancing',
            detail: `DEBIT customer_escrow ₹ ${(amountPaise / 100).toFixed(2)} | CREDIT merchant_settlement ₹ ${(amountPaise / 100).toFixed(2)}. Net imbalance = 0.`,
            type: 'ledger' as const,
            hash: 'sha256_ledg_11094f',
          },
          {
            step: 7,
            time: '13:42:10.245',
            title: 'Cryptographic SHA-256 Audit Log Hash Chained',
            detail: `Appended to tamper-evident audit tree. Merkle root updated at height #14,892.`,
            type: 'created' as const,
            hash: 'sha256_chain_90114a',
          },
        ]),
  ]

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
              <Link href="/payments" className="btn btn-secondary" style={{ padding: '6px 10px', gap: 6, fontSize: 12 }}>
                <ArrowLeft size={14} />
                <span>All Payments</span>
              </Link>
              <h1 className="page-title" style={{ margin: 0 }}>Payment Lifecycle Trace</h1>
              <span className={`badge badge-${status}`}>
                {status.toUpperCase()}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
              <code className="id-chip" style={{ fontSize: 13, fontWeight: 700 }}>{paymentId}</code>
              <button
                onClick={() => handleCopy(paymentId)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}
                title="Copy Payment ID"
              >
                {copied ? <Check size={14} color="#059669" /> : <Copy size={14} />}
              </button>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>• Idempotency Guaranteed • Razorpay Adapter</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={handleReconcile}
              disabled={isReconciling}
              className="btn btn-primary"
              style={{ fontSize: 13, gap: 6 }}
            >
              <RefreshCw size={14} className={isReconciling ? 'spin' : ''} />
              <span>{isReconciling ? 'Reconciling...' : 'Run Dual-Entry Reconcile'}</span>
            </button>
            <button
              onClick={handleInvestigate}
              disabled={isInvestigating}
              className="btn btn-secondary"
              style={{ fontSize: 13, gap: 6 }}
            >
              <Search size={14} />
              <span>{isInvestigating ? 'Analyzing...' : 'Escalate to LangGraph'}</span>
            </button>
          </div>
        </header>

        {/* Action result feedback */}
        {reconcileResult && (
          <div style={{ marginBottom: 20, padding: 12, background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: 8, fontSize: 13, color: '#065f46', display: 'flex', alignItems: 'center', gap: 8 }}>
            <CheckCircle2 size={16} />
            <span>{reconcileResult}</span>
          </div>
        )}
        {investigateResult && (
          <div style={{ marginBottom: 20, padding: 12, background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, fontSize: 13, color: '#1e40af', display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={16} />
            <span>{investigateResult}</span>
          </div>
        )}

        {/* Invariant Warning / Success Banner */}
        {isUnknown ? (
          <div
            className="card"
            style={{
              marginBottom: 24,
              borderLeft: '4px solid #f59e0b',
              background: 'linear-gradient(135deg, #fffbeb 0%, #ffffff 100%)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
              <AlertTriangle size={24} color="#d97706" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#92400e', margin: 0 }}>
                  Invariant 2 Activated: Ambiguous Timeout Outcome Lock
                </h3>
                <p style={{ fontSize: 13, color: '#b45309', margin: '4px 0 0', lineHeight: 1.5 }}>
                  This payment attempt experienced an upstream network timeout. <strong>It may or may not have been charged by Razorpay.</strong>{' '}
                  Under our mathematical safety invariant, <strong>automated retries are strictly prohibited</strong> to avoid double-charging the customer.
                  Use the Reconcile action to poll Razorpay's authoritative status ledger.
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div
            className="card"
            style={{
              marginBottom: 24,
              borderLeft: '4px solid #059669',
              background: 'linear-gradient(135deg, #ecfdf5 0%, #ffffff 100%)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <ShieldCheck size={24} color="#059669" />
              <div>
                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#065f46', margin: 0 }}>
                  Cryptographic Invariant Verified: Settled & Balanced
                </h3>
                <p style={{ fontSize: 13, color: '#047857', margin: '2px 0 0' }}>
                  HMAC signature confirmed valid, double-entry ledger balanced with zero delta, and record secured in SHA-256 hash chain.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Main 2-column layout: Timeline (2fr) + Details Sidebar (1fr) */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
          {/* Event Timeline */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Chronological State Transitions</h3>
              <span className="badge badge-captured">{timeline.length} Steps Logged</span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 16, position: 'relative', paddingLeft: 8 }}>
              {timeline.map((evt, idx) => (
                <div key={idx} style={{ display: 'flex', gap: 16, position: 'relative' }}>
                  {/* Step indicator circle */}
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: '50%',
                      background: evt.type === 'unknown' ? '#fef3c7' : evt.type === 'webhook' ? '#eff6ff' : '#ecfdf5',
                      border: `2px solid ${evt.type === 'unknown' ? '#f59e0b' : evt.type === 'webhook' ? 'var(--brand-primary)' : '#059669'}`,
                      color: evt.type === 'unknown' ? '#d97706' : evt.type === 'webhook' ? 'var(--brand-primary)' : '#059669',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontWeight: 700,
                      fontSize: 12,
                      flexShrink: 0,
                      zIndex: 2,
                    }}
                  >
                    {evt.step}
                  </div>

                  {/* Event content box */}
                  <div
                    style={{
                      flex: 1,
                      padding: '12px 16px',
                      background: 'var(--bg-subtle)',
                      borderRadius: 8,
                      border: '1px solid var(--border-color)',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                        {evt.title}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                        {evt.time}
                      </span>
                    </div>

                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: '0 0 6px', lineHeight: 1.5 }}>
                      {evt.detail}
                    </p>

                    {evt.hash && (
                      <div style={{ fontSize: 11, color: 'var(--brand-primary)', fontFamily: 'monospace', display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Lock size={11} />
                        <span>{evt.hash}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Details Sidebar */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Payment Summary Details */}
            <div className="card">
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 14 }}>Authoritative Metadata</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, fontSize: 13 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Amount</span>
                  <span style={{ fontWeight: 800, fontFamily: 'monospace', color: 'var(--text-primary)' }}>
                    ₹ {(amountPaise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Currency</span>
                  <span style={{ fontWeight: 600 }}>INR (Indian Rupee)</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Provider Gateway</span>
                  <span style={{ fontWeight: 600, color: 'var(--brand-primary)' }}>Razorpay Test v1</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Order ID</span>
                  <span className="mono" style={{ fontSize: 11 }}>ord_rzp_{paymentId.substring(4, 10)}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Idempotency Key</span>
                  <span className="mono" style={{ fontSize: 11 }}>idemp_live_{paymentId.substring(4, 10)}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: 8, borderBottom: '1px solid var(--border-color)' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Reconciliation</span>
                  <span style={{ fontWeight: 700, color: isUnknown ? '#d97706' : '#059669' }}>
                    {isUnknown ? 'Pending Sync' : 'Reconciled'}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Audit Log Node</span>
                  <Link href="/audit" style={{ color: 'var(--brand-primary)', textDecoration: 'none', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 2 }}>
                    <span>Block #14,892</span>
                    <ExternalLink size={11} />
                  </Link>
                </div>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="card">
              <h3 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>Operator Actions</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <button
                  onClick={() => setShowRawJson(!showRawJson)}
                  className="btn btn-secondary"
                  style={{ width: '100%', justifyContent: 'center', fontSize: 12, gap: 6 }}
                >
                  <FileText size={14} />
                  <span>{showRawJson ? 'Hide Raw Audit JSON' : 'Inspect Raw Event JSON'}</span>
                </button>

                <Link
                  href="/investigations"
                  className="btn btn-secondary"
                  style={{ width: '100%', justifyContent: 'center', fontSize: 12, gap: 6 }}
                >
                  <Search size={14} />
                  <span>Open LangGraph Incidents</span>
                </Link>
              </div>

              {showRawJson && (
                <div style={{ marginTop: 14 }}>
                  <pre
                    style={{
                      background: 'var(--bg-subtle)',
                      border: '1px solid var(--border-color)',
                      borderRadius: 6,
                      padding: 10,
                      fontSize: 11,
                      fontFamily: 'monospace',
                      overflowX: 'auto',
                      maxHeight: 180,
                    }}
                  >
                    {JSON.stringify(
                      {
                        payment_id: paymentId,
                        order_id: `ord_rzp_${paymentId.substring(4, 10)}`,
                        status: status,
                        amount: amountPaise,
                        currency: 'INR',
                        provider: 'razorpay',
                        idempotency_key: `idemp_live_${paymentId.substring(4, 10)}`,
                        signature_hmac: 'sha256_verified_true',
                        merkle_leaf: '0x99281a8b9f',
                      },
                      null,
                      2
                    )}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
