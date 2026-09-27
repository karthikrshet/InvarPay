'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface KPI {
  label: string
  value: string
  delta?: string
  icon: string
  color: string
}

interface Payment {
  id: string
  status: string
  amount: number
  currency: string
  created_at: string
  provider_payment_id?: string
}
import { Sidebar } from '../components/Sidebar'

function StatusBadge({ status }: { status: string }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{status}</span>
}

function KPICard({ kpi }: { kpi: KPI }) {
  return (
    <div className="card" style={{ cursor: 'default' }}>
      <div className="card-header">
        <div>
          <div className="card-title">{kpi.label}</div>
          <div className="card-value">{kpi.value}</div>
          {kpi.delta && <div className="card-delta">↑ {kpi.delta}</div>}
        </div>
        <div className="card-icon" style={{ background: kpi.color, fontSize: 20 }}>
          {kpi.icon}
        </div>
      </div>
      <div className="card-body" />
    </div>
  )
}

function formatAmount(amount: number, currency: string): string {
  return `${currency} ${(amount / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
  })
}

export default function DashboardPage() {
  const [health, setHealth] = useState<{ status: string; checks?: Record<string, boolean> } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`${API_URL}/health/ready`)
      .then(r => r.json())
      .then(data => { setHealth(data); setLoading(false) })
      .catch(e => { setError('API unavailable — is the server running?'); setLoading(false) })
  }, [])

  const kpis: KPI[] = [
    { label: 'Total Payments', value: '—', icon: '₹', color: 'rgba(99,102,241,0.15)' },
    { label: 'Success Rate', value: '—', icon: '✓', color: 'rgba(16,185,129,0.15)' },
    { label: 'Unknown Outcomes', value: '—', delta: 'Needs reconciliation', icon: '⚠', color: 'rgba(245,158,11,0.15)' },
    { label: 'Avg Latency', value: '—', icon: '⚡', color: 'rgba(59,130,246,0.15)' },
  ]

  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <div className="page-header">
          <div className="flex items-center justify-between">
            <div>
              <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: -0.3 }}>
                Payment Operations Dashboard
              </h1>
              <p style={{ color: 'var(--text-muted)', fontSize: 13, marginTop: 4 }}>
                Real-time payment reliability metrics · Razorpay TEST MODE · SYNTHETIC demo data
              </p>
            </div>
            <div className="flex gap-2">
              <a href="http://localhost:8000/docs" target="_blank" className="btn btn-ghost" style={{ fontSize: 12 }}>
                API Docs ↗
              </a>
            </div>
          </div>
        </div>

        <div className="page-body">
          {/* API Health Banner */}
          {loading ? (
            <div className="alert alert-info" style={{ marginBottom: 24 }}>
              <span className="animate-spin">⟳</span> Connecting to InvarPay API...
            </div>
          ) : error ? (
            <div className="alert alert-warning" style={{ marginBottom: 24 }}>
              ⚠️ {error} — Run <code style={{ fontFamily: 'monospace', background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: 4 }}>make dev</code> to start the stack.
            </div>
          ) : (
            <div className="alert alert-success" style={{ marginBottom: 24 }}>
              ✓ InvarPay API connected · DB: {health?.checks?.database ? '✓' : '✗'} · Redis: {health?.checks?.redis ? '✓' : '✗'}
            </div>
          )}

          {/* KPI Grid */}
          <div className="kpi-grid">
            {kpis.map(k => <KPICard key={k.label} kpi={k} />)}
          </div>

          {/* State Machine Reference */}
          <div className="card" style={{ marginBottom: 24 }}>
            <div className="card-header">
              <div className="card-title">Payment State Machine</div>
            </div>
            <div className="card-body">
              <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
                {['created', 'initiated', 'pending', 'authorized', 'captured', 'failed', 'cancelled', 'unknown'].map(s => (
                  <StatusBadge key={s} status={s} />
                ))}
              </div>
              <div className="alert alert-warning" style={{ marginTop: 16, fontSize: 12 }}>
                🔒 <strong>Safety invariant:</strong> <code className="mono">unknown</code> ≠ <code className="mono">failed</code>.
                A network timeout never authorizes retry. Reconcile first.
              </div>
            </div>
          </div>

          {/* Quick links */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <Link href="/payments" className="card" style={{ padding: 20, cursor: 'pointer', textDecoration: 'none' }}>
              <div className="flex items-center gap-3">
                <div className="card-icon" style={{ background: 'rgba(99,102,241,0.15)' }}>₹</div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>View Payments</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 2 }}>Track all attempts</div>
                </div>
              </div>
            </Link>
            <Link href="/investigations" className="card" style={{ padding: 20, cursor: 'pointer', textDecoration: 'none' }}>
              <div className="flex items-center gap-3">
                <div className="card-icon" style={{ background: 'rgba(245,158,11,0.15)' }}>🔍</div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>Investigations</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 2 }}>AI-assisted analysis</div>
                </div>
              </div>
            </Link>
            <Link href="/audit" className="card" style={{ padding: 20, cursor: 'pointer', textDecoration: 'none' }}>
              <div className="flex items-center gap-3">
                <div className="card-icon" style={{ background: 'rgba(16,185,129,0.15)' }}>🔒</div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>Audit Log</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 2 }}>Hash-chained events</div>
                </div>
              </div>
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
