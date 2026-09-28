'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Sidebar } from '../../components/Sidebar'
import {
  Bot,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  ExternalLink,
  RotateCcw,
  Sparkles,
  Layers,
  FileText,
} from 'lucide-react'

interface Investigation {
  id: string
  payment_id: string
  status: 'RESOLVED' | 'AWAITING_APPROVAL' | 'INVESTIGATING'
  finding: string
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  steps: string[]
  proposed_action: string
  created_at: string
}

export default function InvestigationsPage() {
  const [investigations, setInvestigations] = useState<Investigation[]>([
    {
      id: 'inv_01J8K901_LGR',
      payment_id: 'pay_01J8K3R4P9M01',
      status: 'RESOLVED',
      risk_level: 'LOW',
      finding: 'Payment authorization timeout resolved via deterministic outbox trace. Provider webhook HMAC signature validated with 0.4ms latency. Zero double charge risk.',
      steps: [
        '1. Ingested ambiguous webhook payload (event: payment.authorized.timeout).',
        '2. Queried Razorpay test-mode gateway status API (got: captured, id: rzp_test_pay_9941a).',
        '3. Reconciled dual-entry ledger (Dr. Gateway / Cr. Merchant Cash matched 100%).',
        '4. Emitted cryptographically chained audit log entry (SHA-256 verified).',
      ],
      proposed_action: 'Mark payment as CAPTURED and notify merchant webhook.',
      created_at: new Date(Date.now() - 1000 * 60 * 18).toISOString(),
    },
    {
      id: 'inv_01J8K902_LGR',
      payment_id: 'pay_01J8K3Q8N2B02',
      status: 'AWAITING_APPROVAL',
      risk_level: 'HIGH',
      finding: 'Provider returned network 504 Gateway Timeout during capture call. Policy engine blocked automated blind retry to prevent duplicate debit. Human operator review required.',
      steps: [
        '1. Detected network drop during payment transition: INITIATED → CAPTURE.',
        '2. Policy engine evaluated DENY-BY-DEFAULT guardrails: retry attempt limit reached (1/1).',
        '3. Replay defense verified: timestamp within 300s window.',
        '4. Generated safe recovery proposal awaiting human confirmation.',
      ],
      proposed_action: 'Initiate manual bank UTR enquiry before triggering reverse refund.',
      created_at: new Date(Date.now() - 1000 * 60 * 35).toISOString(),
    },
    {
      id: 'inv_01J8K903_LGR',
      payment_id: 'pay_01J8K3M1K7C03',
      status: 'RESOLVED',
      risk_level: 'LOW',
      finding: 'High-velocity transaction cluster (3 orders in 90 seconds). PaymentGraph AI classified as normal merchant sales spike based on verified IP fingerprint.',
      steps: [
        '1. PaymentGraph heuristic triggered: rule PG001 (Velocity Spike alert).',
        '2. LangGraph agent retrieved customer 90-day history (trust score: 98/100).',
        '3. Evaluated chargeback risk: < 0.01% probability.',
        '4. Auto-cleared step-up verification and authorized charge.',
      ],
      proposed_action: 'Auto-authorize charge without blocking customer.',
      created_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    },
  ])

  const handleApprove = (id: string) => {
    setInvestigations(prev =>
      prev.map(inv =>
        inv.id === id ? { ...inv, status: 'RESOLVED' as const } : inv
      )
    )
  }

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 className="page-title">LangGraph Dispute & Incident Agent</h1>
              <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Bot size={12} />
                <span>STATEFUL GRAPH REASONING</span>
              </span>
            </div>
            <p className="page-subtitle">Autonomous multi-step dispute investigation triage with deterministic safety policy guardrails</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>POLICY ENFORCED (DENY-BY-DEFAULT)</span>
          </div>
        </header>

        <div className="page-body">
          {/* Top Safety Banner */}
          <div className="alert alert-info" style={{ marginBottom: 24, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 34, height: 34, borderRadius: 8, background: '#dbeafe', color: '#1d4ed8', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ShieldCheck size={18} />
              </div>
              <div>
                <strong>Autonomous Safety Invariant:</strong> The investigation agent operates under strict <strong>deny-by-default</strong> policy rules.
                It can gather evidence, query logs, and compute trust heuristics, but cannot execute financial refunds or mutations without explicit human approval.
              </div>
            </div>
            <span className="badge badge-success" style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
              ZERO HALLUCINATION DEFENSE
            </span>
          </div>

          {/* Investigation Cases Grid */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {investigations.map(inv => (
              <div
                key={inv.id}
                className="card"
                style={{
                  borderLeft: `5px solid ${
                    inv.status === 'RESOLVED' ? '#10b981' : inv.risk_level === 'HIGH' ? '#ef4444' : '#f59e0b'
                  }`,
                }}
              >
                <div className="card-header" style={{ background: '#f8fafc' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{ width: 28, height: 28, borderRadius: 6, background: '#e0e7ff', color: '#4338ca', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      <Bot size={16} />
                    </div>
                    <div>
                      <span className="mono" style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>
                        {inv.id}
                      </span>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)', marginLeft: 10 }}>
                        Target: <Link href={`/payments/${inv.payment_id}`} style={{ fontWeight: 600 }}>{inv.payment_id}</Link>
                      </span>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className={`badge badge-${inv.risk_level === 'LOW' ? 'captured' : inv.risk_level === 'HIGH' ? 'failed' : 'pending'}`}>
                      {inv.risk_level} RISK
                    </span>
                    <span className={`badge badge-${inv.status === 'RESOLVED' ? 'captured' : 'pending'}`}>
                      {inv.status}
                    </span>
                  </div>
                </div>

                <div className="card-body">
                  <div style={{ marginBottom: 14 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 4 }}>
                      AGENT FINDINGS & REASONING SUMMARY
                    </div>
                    <p style={{ fontSize: 13.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                      {inv.finding}
                    </p>
                  </div>

                  {/* Step by Step Execution Chain */}
                  <div style={{ background: '#f8fafc', padding: '14px 18px', borderRadius: 10, border: '1px solid #e2e8f0', marginBottom: 16 }}>
                    <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
                      LangGraph Node Traversal Trace
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {inv.steps.map((st, i) => (
                        <div key={i} style={{ fontSize: 12, fontFamily: 'JetBrains Mono', color: '#334155' }}>
                          {st}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Proposed Action & Approval Gate */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
                    <div>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Proposed Recommendation: </span>
                      <strong style={{ fontSize: 13, color: 'var(--text-primary)' }}>{inv.proposed_action}</strong>
                    </div>

                    <div>
                      {inv.status === 'AWAITING_APPROVAL' ? (
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button
                            onClick={() => handleApprove(inv.id)}
                            className="btn btn-primary btn-sm"
                            style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                          >
                            <CheckCircle2 size={13} />
                            <span>Confirm & Approve Action</span>
                          </button>
                          <button className="btn btn-outline btn-sm">Reject</button>
                        </div>
                      ) : (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: '#059669', fontSize: 12, fontWeight: 700 }}>
                          <CheckCircle2 size={14} />
                          <span>Action Executed & Logged to SHA-256 Ledger</span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
