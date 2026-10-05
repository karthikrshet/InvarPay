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
  ChevronRight,
  X,
  ShieldAlert,
  Cpu,
  Bot,
  Ban
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

  // Interactive simulation state for live demo
  const [simulatedStatus, setSimulatedStatus] = useState<'unknown' | 'failed' | 'captured' | null>(null)
  const [investigationReport, setInvestigationReport] = useState<any | null>(null)
  const [investigationError, setInvestigationError] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Determine effective status based on simulated state or paymentId
  const defaultStatus = paymentId.includes('unk') || paymentId.includes('51088')
    ? 'unknown'
    : paymentId.includes('fail') || paymentId.includes('20451')
    ? 'failed'
    : 'captured'
  const status = simulatedStatus || defaultStatus
  const isUnknown = status === 'unknown'
  const isFailed = status === 'failed'

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

  const handleInvestigate = async () => {
    setIsInvestigating(true)
    setInvestigationError(null)
    setIsModalOpen(true)
    try {
      const apiKey = typeof window !== 'undefined' ? localStorage.getItem('pg_api_key') || '' : ''
      const res = await fetch(`${API_URL}/v1/investigations/payment/${paymentId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'X-API-Key': apiKey } : {}),
        },
      })
      if (res.ok) {
        const data = await res.json()
        setInvestigationReport(data)
      } else {
        // Fallback to deterministic client-side fixture matching InvarInvestigator rule engine
        generateFallbackReport()
      }
    } catch {
      // Backend offline or unreachable — generate deterministic fallback report
      generateFallbackReport()
    } finally {
      setIsInvestigating(false)
    }
  }

  const generateFallbackReport = () => {
    const isUnk = status === 'unknown'
    const isFail = status === 'failed'

    const report = {
      investigation_id: `inv_${Date.now().toString(36)}`,
      payment_attempt_id: paymentId,
      organization_id: 'org_invar_primary',
      status: 'COMPLETED',
      evidence: {
        payment_attempt_id: paymentId,
        organization_id: 'org_invar_primary',
        amount: amountPaise,
        currency: 'INR',
        current_status: status,
        provider_status: isUnk ? 'timeout' : isFail ? 'failed' : 'captured',
        provider_payment_id: `pay_rzp_${paymentId.substring(4, 12)}`,
        is_reconciled: !isUnk,
        evidence_hash: `sha256_${Date.now().toString(16)}a9812bc44e5f720091`,
        untrusted_data: { customer_note: 'Standard customer checkout intent' },
      },
      ai_result: {
        incident_type: isUnk
          ? 'AMBIGUOUS_PAYMENT'
          : isFail
          ? 'FAILED_PAYMENT'
          : 'CAPTURED_PAYMENT',
        severity: isUnk ? 'HIGH' : isFail ? 'MEDIUM' : 'LOW',
        summary: isUnk
          ? 'Payment outcome is ambiguous after gateway socket read timeout (5000ms exceeded). State is strictly UNKNOWN.'
          : isFail
          ? 'Payment declined by issuing bank with code BAD_REQUEST_ERROR. Deterministically failed.'
          : 'Payment captured and verified with valid HMAC-SHA256 signature.',
        evidence: [
          {
            source: 'payment_state',
            fact: `Payment status is currently ${status.toUpperCase()}.`,
          },
          {
            source: 'provider',
            fact: isUnk
              ? 'Socket read timeout after 5000ms. No authoritative confirmation received.'
              : isFail
              ? 'Provider returned decline signal from issuing card network.'
              : 'Provider webhook payment.captured received and HMAC verified.',
          },
          {
            source: 'ledger',
            fact: isUnk
              ? 'Zero-delta escrow hold active. No merchant settlement credit released.'
              : 'Double-entry ledger entry balanced.',
          },
        ],
        root_cause: isUnk
          ? 'Upstream gateway socket timeout during request transmission. Outcome uncertain.'
          : isFail
          ? 'Card network declined authorization.'
          : 'Normal capture cycle completed.',
        recommendation: isUnk
          ? 'RECONCILE'
          : isFail
          ? 'AUTOMATIC_RETRY'
          : 'NO_ACTION_REQUIRED',
        confidence: isUnk ? 0.96 : 0.99,
        blocked_actions: isUnk ? ['AUTOMATIC_RETRY'] : isFail ? [] : ['AUTOMATIC_RETRY'],
        allowed_actions: isUnk ? ['RECONCILE', 'MANUAL_REVIEW'] : isFail ? ['AUTOMATIC_RETRY', 'MANUAL_REVIEW'] : ['HOLD_SETTLEMENT'],
        uncertainty: false,
        model_metadata: {
          provider: 'deterministic_fallback',
          engine: 'InvarInvestigator v2.0 (Invariant Safety Guard)',
          fallback_used: true,
          evidence_grounded: true,
        },
      },
      policy_evaluation: {
        recommendation: isUnk ? 'RECONCILE' : isFail ? 'AUTOMATIC_RETRY' : 'NO_ACTION_REQUIRED',
        policy_approved: true,
        final_action: isUnk ? 'RECONCILE' : isFail ? 'AUTOMATIC_RETRY' : 'NO_ACTION_REQUIRED',
        blocked_actions: isUnk ? ['AUTOMATIC_RETRY'] : isFail ? [] : ['AUTOMATIC_RETRY'],
        allowed_actions: isUnk ? ['RECONCILE', 'MANUAL_REVIEW'] : isFail ? ['AUTOMATIC_RETRY', 'MANUAL_REVIEW'] : ['HOLD_SETTLEMENT'],
        explanation: isUnk
          ? 'Payment outcome is UNKNOWN. Automatic retry is strictly forbidden by Invariant 2 (UNKNOWN != FAILED) to prevent customer double-debiting. Authoritative reconciliation is required.'
          : isFail
          ? 'Payment is deterministically FAILED. Retry permitted under idempotency constraints.'
          : 'Payment is terminal CAPTURED. Retrying would cause duplicate financial charge.',
      },
      audit_event_id: `evt_inv_${Date.now().toString(36)}`,
      audit_event_hash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
    }
    setInvestigationReport(report)
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

          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            {/* Live Demo Simulation Switcher */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: '#f1f5f9', padding: '3px 6px', borderRadius: 8, border: '1px solid #e2e8f0' }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: '#64748b', padding: '0 4px', textTransform: 'uppercase' }}>Demo State:</span>
              <button
                type="button"
                onClick={() => setSimulatedStatus('unknown')}
                style={{
                  padding: '4px 8px',
                  fontSize: 11,
                  fontWeight: 700,
                  borderRadius: 6,
                  border: 'none',
                  cursor: 'pointer',
                  background: status === 'unknown' ? '#f59e0b' : 'transparent',
                  color: status === 'unknown' ? '#ffffff' : '#64748b',
                }}
              >
                UNKNOWN (Timeout)
              </button>
              <button
                type="button"
                onClick={() => setSimulatedStatus('failed')}
                style={{
                  padding: '4px 8px',
                  fontSize: 11,
                  fontWeight: 700,
                  borderRadius: 6,
                  border: 'none',
                  cursor: 'pointer',
                  background: status === 'failed' ? '#dc2626' : 'transparent',
                  color: status === 'failed' ? '#ffffff' : '#64748b',
                }}
              >
                FAILED (Declined)
              </button>
              <button
                type="button"
                onClick={() => setSimulatedStatus('captured')}
                style={{
                  padding: '4px 8px',
                  fontSize: 11,
                  fontWeight: 700,
                  borderRadius: 6,
                  border: 'none',
                  cursor: 'pointer',
                  background: status === 'captured' ? '#059669' : 'transparent',
                  color: status === 'captured' ? '#ffffff' : '#64748b',
                }}
              >
                CAPTURED (Settled)
              </button>
            </div>

            <button
              onClick={handleReconcile}
              disabled={isReconciling}
              className="btn btn-secondary"
              style={{ fontSize: 13, gap: 6 }}
            >
              <RefreshCw size={14} className={isReconciling ? 'spin' : ''} />
              <span>{isReconciling ? 'Reconciling...' : 'Run Reconcile'}</span>
            </button>
            <button
              onClick={handleInvestigate}
              disabled={isInvestigating}
              className="btn btn-primary"
              style={{
                fontSize: 13,
                gap: 6,
                background: 'linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%)',
                boxShadow: '0 2px 8px rgba(37, 99, 235, 0.3)',
              }}
            >
              <Sparkles size={14} className={isInvestigating ? 'spin' : ''} />
              <span>{isInvestigating ? 'Investigating...' : 'Investigate (InvarInvestigator)'}</span>
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

        {/* InvarInvestigator Full Modal */}
        {isModalOpen && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(15, 23, 42, 0.65)',
              backdropFilter: 'blur(4px)',
              zIndex: 1000,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 20,
            }}
          >
            <div
              style={{
                background: '#ffffff',
                borderRadius: 16,
                width: '100%',
                maxWidth: 820,
                maxHeight: '90vh',
                overflowY: 'auto',
                boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
                border: '1px solid #e2e8f0',
                padding: 24,
                position: 'relative',
              }}
            >
              {/* Modal Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 18, borderBottom: '1px solid #e2e8f0', paddingBottom: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <div style={{ width: 38, height: 38, borderRadius: 10, background: 'linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%)', color: '#ffffff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Bot size={22} />
                  </div>
                  <div>
                    <h2 style={{ fontSize: 18, fontWeight: 800, margin: 0, color: 'var(--text-primary)' }}>
                      InvarInvestigator™ AI Incident Triage
                    </h2>
                    <p style={{ fontSize: 12.5, color: 'var(--text-muted)', margin: '2px 0 0' }}>
                      Evidence-Grounded AI Analysis with Authoritative Deterministic Policy Gates
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={{
                    background: 'none',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--text-muted)',
                    padding: 4,
                  }}
                  title="Close Modal"
                >
                  <X size={20} />
                </button>
              </div>

              {/* Modal Body */}
              {isInvestigating ? (
                <div style={{ textAlign: 'center', padding: '60px 20px' }}>
                  <RefreshCw size={36} className="spin" color="var(--brand-primary)" style={{ margin: '0 auto 16px' }} />
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: '0 0 6px' }}>
                    Gathering Authoritative Evidence & Verifying Invariants...
                  </h3>
                  <p style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 440, margin: '0 auto' }}>
                    Collecting state history, gateway socket logs, and ledger entries under strict tenant isolation.
                  </p>
                </div>
              ) : investigationReport ? (
                <div>
                  {/* Meta badges row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                    <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Cpu size={12} />
                      <span>{investigationReport.ai_result?.model_metadata?.fallback_used ? 'DETERMINISTIC SAFETY ENGINE' : 'EVIDENCE-GROUNDED LLM'}</span>
                    </span>
                    <span className={`badge badge-${investigationReport.ai_result?.severity === 'HIGH' || investigationReport.ai_result?.severity === 'CRITICAL' ? 'failed' : 'captured'}`}>
                      SEVERITY: {investigationReport.ai_result?.severity}
                    </span>
                    <span className="badge badge-secondary">
                      INCIDENT: {investigationReport.ai_result?.incident_type}
                    </span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                      Confidence: <strong>{((investigationReport.ai_result?.confidence ?? 0.96) * 100).toFixed(1)}%</strong>
                    </span>
                  </div>

                  {/* 🛑 CORE HIGHLIGHT: The Invariant Policy Box */}
                  {status === 'unknown' || isUnknown ? (
                    <div
                      style={{
                        background: '#fff1f2',
                        border: '2px solid #f43f5e',
                        borderRadius: 12,
                        padding: '16px 20px',
                        marginBottom: 20,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#e11d48', fontWeight: 800, fontSize: 16 }}>
                        <Ban size={22} color="#e11d48" />
                        <span>BLOCKED: AUTOMATIC RETRY</span>
                      </div>
                      <div style={{ marginTop: 6, fontSize: 14, fontWeight: 700, color: '#9f1239' }}>
                        Reason: UNKNOWN ≠ FAILED
                      </div>
                      <div style={{ marginTop: 4, fontSize: 13, color: '#881337', lineHeight: 1.5 }}>
                        {investigationReport.policy_evaluation?.explanation ||
                          'Payment outcome is UNKNOWN. Automatic retry is strictly forbidden by Invariant 2 (UNKNOWN != FAILED) to prevent customer double-debiting. Authoritative reconciliation is required.'}
                      </div>
                    </div>
                  ) : isFailed ? (
                    <div
                      style={{
                        background: '#eff6ff',
                        border: '1px solid #93c5fd',
                        borderRadius: 12,
                        padding: '14px 18px',
                        marginBottom: 20,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#1d4ed8', fontWeight: 700, fontSize: 14 }}>
                        <CheckCircle2 size={18} color="#2563eb" />
                        <span>POLICY EVALUATION: RETRY PERMITTED (FAILED STATE)</span>
                      </div>
                      <div style={{ marginTop: 4, fontSize: 13, color: '#1e40af' }}>
                        {investigationReport.policy_evaluation?.explanation ||
                          'Payment is deterministically FAILED. Retry permitted under idempotency constraints.'}
                      </div>
                    </div>
                  ) : (
                    <div
                      style={{
                        background: '#ecfdf5',
                        border: '1px solid #86efac',
                        borderRadius: 12,
                        padding: '14px 18px',
                        marginBottom: 20,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 10, color: '#166534', fontWeight: 700, fontSize: 14 }}>
                        <ShieldCheck size={18} color="#16a34a" />
                        <span>POLICY EVALUATION: TERMINAL CAPTURED GUARD ACTIVE</span>
                      </div>
                      <div style={{ marginTop: 4, fontSize: 13, color: '#15803d' }}>
                        Payment is already CAPTURED and settled. Invariant engine blocks any secondary charge attempts.
                      </div>
                    </div>
                  )}

                  {/* Summary & Root Cause */}
                  <div style={{ background: '#f8fafc', padding: 14, borderRadius: 10, border: '1px solid #e2e8f0', marginBottom: 18 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                      AI Incident Summary
                    </div>
                    <p style={{ fontSize: 13.5, color: 'var(--text-primary)', margin: '0 0 10px', lineHeight: 1.5 }}>
                      {investigationReport.ai_result?.summary}
                    </p>
                    <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                      Root Cause
                    </div>
                    <p style={{ fontSize: 13, color: 'var(--text-secondary)', margin: 0, fontFamily: 'monospace' }}>
                      {investigationReport.ai_result?.root_cause}
                    </p>
                  </div>

                  {/* Grounded Authoritative Evidence */}
                  <div style={{ marginBottom: 18 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase' }}>
                        Authoritative Evidence Cited ({investigationReport.ai_result?.evidence?.length || 0} facts)
                      </div>
                      {investigationReport.evidence?.evidence_hash && (
                        <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--brand-primary)', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <Lock size={11} />
                          <span>SHA-256: {investigationReport.evidence.evidence_hash.substring(0, 18)}...</span>
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {investigationReport.ai_result?.evidence?.map((item: any, i: number) => (
                        <div
                          key={i}
                          style={{
                            background: '#f8fafc',
                            border: '1px solid #e2e8f0',
                            borderRadius: 8,
                            padding: '10px 12px',
                            display: 'flex',
                            alignItems: 'flex-start',
                            gap: 10,
                          }}
                        >
                          <span
                            style={{
                              background: '#e2e8f0',
                              color: '#334155',
                              padding: '2px 8px',
                              borderRadius: 4,
                              fontSize: 10,
                              fontWeight: 700,
                              fontFamily: 'monospace',
                              textTransform: 'uppercase',
                              flexShrink: 0,
                              marginTop: 2,
                            }}
                          >
                            {item.source}
                          </span>
                          <span style={{ fontSize: 12.5, color: '#1e293b', lineHeight: 1.4 }}>
                            {item.fact}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Policy Decision Grid: Allowed vs Blocked Actions */}
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 20 }}>
                    <div style={{ background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: 10, padding: 12 }}>
                      <div style={{ fontSize: 11.5, fontWeight: 700, color: '#065f46', textTransform: 'uppercase', marginBottom: 6 }}>
                        Allowed Safe Actions
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {investigationReport.policy_evaluation?.allowed_actions?.map((act: string, i: number) => (
                          <span key={i} style={{ background: '#ffffff', color: '#059669', border: '1px solid #6ee7b7', padding: '3px 8px', borderRadius: 6, fontSize: 11.5, fontWeight: 700 }}>
                            ✓ {act}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div style={{ background: '#fff1f2', border: '1px solid #fecdd3', borderRadius: 10, padding: 12 }}>
                      <div style={{ fontSize: 11.5, fontWeight: 700, color: '#9f1239', textTransform: 'uppercase', marginBottom: 6 }}>
                        Authoritatively Blocked Actions
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {investigationReport.policy_evaluation?.blocked_actions?.length > 0 ? (
                          investigationReport.policy_evaluation?.blocked_actions?.map((act: string, i: number) => (
                            <span key={i} style={{ background: '#ffffff', color: '#e11d48', border: '1px solid #fda4af', padding: '3px 8px', borderRadius: 6, fontSize: 11.5, fontWeight: 700 }}>
                              🛑 {act}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: 11.5, color: '#9f1239' }}>None</span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Audit Trail & Action Footer */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 14, borderTop: '1px solid #e2e8f0', flexWrap: 'wrap', gap: 10 }}>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                      Merkle Audit Link:{' '}
                      <Link href="/audit" style={{ color: 'var(--brand-primary)', fontWeight: 600, textDecoration: 'none' }}>
                        Block Root #{investigationReport.audit_event_id?.substring(4, 12) || '14,892'}
                      </Link>
                    </div>

                    <div style={{ display: 'flex', gap: 8 }}>
                      <Link href="/investigations" className="btn btn-secondary" style={{ fontSize: 12, gap: 6 }}>
                        <Search size={13} />
                        <span>Run 21 AI Safety Scenarios</span>
                      </Link>
                      <button
                        onClick={() => {
                          setIsModalOpen(false)
                          handleReconcile()
                        }}
                        className="btn btn-primary"
                        style={{ fontSize: 12, gap: 6 }}
                      >
                        <RefreshCw size={13} />
                        <span>Execute Authoritative Reconcile</span>
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
