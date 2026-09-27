'use client'

import { useEffect, useState } from 'react'
import { Sidebar } from '../../components/Sidebar'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function SettingsPage() {
  const [health, setHealth] = useState<any>(null)

  useEffect(() => {
    fetch(`${API_URL}/health/ready`)
      .then(res => res.json())
      .then(data => setHealth(data))
      .catch(() => {})
  }, [])

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Settings & Provider Adapters</h1>
            <p className="page-subtitle">Multi-tenant credentials, webhook endpoints & feature flags</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>TEST MODE ENVIRONMENT</span>
          </div>
        </header>

        {/* Provider Connection Card */}
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Payment Gateway Integration</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 20 }}>
            <div style={{ padding: 16, border: '1px solid var(--color-border)', borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>Razorpay Adapter</span>
                <span className="badge badge-pending">TEST MODE ONLY</span>
              </div>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, marginBottom: 12 }}>
                Official Razorpay API integration with HMAC-SHA256 signature verification.
              </p>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                <div>Key ID: <code>rzp_test_***</code> (from env)</div>
                <div style={{ marginTop: 4 }}>Webhook Secret: <code>Configured</code></div>
              </div>
            </div>

            <div style={{ padding: 16, border: '1px solid var(--color-border)', borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontWeight: 600 }}>Fake Provider Adapter</span>
                <span className="badge badge-captured">CI / ACTIVE</span>
              </div>
              <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, marginBottom: 12 }}>
                Deterministic simulation adapter for automated unit, integration, and chaos testing.
              </p>
              <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>
                <div>State Transitions: <code>Fully Deterministic</code></div>
                <div style={{ marginTop: 4 }}>Chaos Fault Injection: <code>Supported</code></div>
              </div>
            </div>
          </div>
        </div>

        {/* Feature Flags Status */}
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Platform Feature Flags</h2>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Module</th>
                  <th>Flag Key</th>
                  <th>Status</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>InvarPay Core</td>
                  <td><code>core_reliability</code></td>
                  <td><span className="badge badge-captured">ENABLED</span></td>
                  <td>Payment attempt tracking, state machine & reconciliation</td>
                </tr>
                <tr>
                  <td>PaymentGraph AI</td>
                  <td><code>feature_paymentgraph</code></td>
                  <td><span className="badge badge-captured">ENABLED</span></td>
                  <td>Explainable fraud rules & risk calibration benchmark</td>
                </tr>
                <tr>
                  <td>PayDev AI</td>
                  <td><code>feature_paydev</code></td>
                  <td><span className="badge badge-captured">ENABLED</span></td>
                  <td>Static repo analyzer, float currency & secret scanner</td>
                </tr>
                <tr>
                  <td>MerchantOS AI</td>
                  <td><code>feature_merchantos</code></td>
                  <td><span className="badge badge-captured">ENABLED</span></td>
                  <td>Invoices, settlements & cashflow forecasting</td>
                </tr>
                <tr>
                  <td>ShopAgent MCP</td>
                  <td><code>feature_shopagent</code></td>
                  <td><span className="badge badge-captured">ENABLED</span></td>
                  <td>Catalog, inventory & buyer confirmation gate</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* System Health */}
        {health && (
          <div className="card">
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Infrastructure Health</h2>
            <div style={{ display: 'flex', gap: 24 }}>
              <div>
                <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>PostgreSQL Authoritative DB: </span>
                <span style={{ fontWeight: 600, color: health.checks?.database ? '#10b981' : '#f59e0b' }}>
                  {health.checks?.database ? 'CONNECTED' : 'LOCAL / STANDBY'}
                </span>
              </div>
              <div>
                <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Redis Cache / Queue: </span>
                <span style={{ fontWeight: 600, color: health.checks?.redis ? '#10b981' : '#f59e0b' }}>
                  {health.checks?.redis ? 'CONNECTED' : 'LOCAL / STANDBY'}
                </span>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
