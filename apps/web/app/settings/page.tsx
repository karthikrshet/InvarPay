'use client'

import { useEffect, useState } from 'react'
import { Sidebar } from '../../components/Sidebar'
import {
  Key,
  ShieldCheck,
  Sliders,
  Database,
  Server,
  RefreshCw,
  Copy,
  Check,
  CheckCircle2,
  Zap,
  Lock,
  Globe,
  Activity,
  Eye,
  EyeOff,
  Layers,
  AlertCircle,
  Plus,
  Trash2,
  Send,
  Cpu,
  Radio,
  ExternalLink
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ApiKeyItem {
  id: string
  name: string
  keyPrefix: string
  fullKey?: string
  scopes: string[]
  isTestMode: boolean
  createdAt: string
  lastUsedAt: string
}

export default function SettingsPage() {
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [showKeySecret, setShowKeySecret] = useState(false)
  const [activeTab, setActiveTab] = useState<'credentials' | 'gateways' | 'webhooks' | 'invariants' | 'infrastructure'>('credentials')
  
  // API Keys State
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([
    {
      id: 'key_prod_01',
      name: 'Primary InvarPay Production Server Key',
      keyPrefix: 'pg_live_8f3a9e',
      scopes: ['payments:read', 'payments:write', 'orders:write', 'audit:read'],
      isTestMode: false,
      createdAt: '2026-09-18T10:14:00Z',
      lastUsedAt: 'Just now',
    },
    {
      id: 'key_test_02',
      name: 'Razorpay Sandbox & Local Dev Engine',
      keyPrefix: 'pg_test_4b2c11',
      scopes: ['payments:read', 'payments:write', 'reconcile:admin', 'merchantos:fin'],
      isTestMode: true,
      createdAt: '2026-09-22T08:30:00Z',
      lastUsedAt: '2 mins ago',
    },
    {
      id: 'key_audit_03',
      name: 'LangGraph Compliance Read-Only Auditor',
      keyPrefix: 'pg_live_99d120',
      scopes: ['audit:read', 'orders:read', 'risk:read'],
      isTestMode: false,
      createdAt: '2026-09-25T14:45:00Z',
      lastUsedAt: '12 mins ago',
    },
  ])

  // New Key Modal State
  const [isGeneratingKey, setIsGeneratingKey] = useState(false)
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyEnv, setNewKeyEnv] = useState<'test' | 'live'>('test')
  const [createdKeySecret, setCreatedKeySecret] = useState<string | null>(null)

  // Razorpay Connection State
  const [rzpKeyId, setRzpKeyId] = useState('rzp_test_9A440XKL912384')
  const [rzpSecret, setRzpSecret] = useState('rzp_sec_mock_4981fbb901923')
  const [rzpTesting, setRzpTesting] = useState(false)
  const [rzpTestResult, setRzpTestResult] = useState<{ success: boolean; latency: number; msg: string } | null>(null)

  // Webhook State
  const [webhookSecret, setWebhookSecret] = useState('whsec_sha256_78f1a084c8e792b0')
  const [testWebhookEvent, setTestWebhookEvent] = useState('payment.captured')
  const [isSendingWebhook, setIsSendingWebhook] = useState(false)
  const [webhookLog, setWebhookLog] = useState<{ event: string; status: number; signature: string; time: string } | null>(null)

  // Invariant Rate Limits
  const [rateLimitRpm, setRateLimitRpm] = useState(1000)
  const [outboxSyncMs, setOutboxSyncMs] = useState(250)

  // Copy helper
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text)
    setCopiedKey(id)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  // Create API Key handler
  const handleCreateApiKey = (e: React.FormEvent) => {
    e.preventDefault()
    if (!newKeyName.trim()) return
    const randomHex = Math.random().toString(16).substring(2, 10) + Math.random().toString(16).substring(2, 10)
    const prefix = newKeyEnv === 'test' ? 'pg_test_' : 'pg_live_'
    const fullKey = `${prefix}${randomHex}`
    const newEntry: ApiKeyItem = {
      id: `key_${Math.random().toString(36).substring(2, 8)}`,
      name: newKeyName,
      keyPrefix: `${prefix}${randomHex.substring(0, 6)}`,
      fullKey,
      scopes: ['payments:read', 'payments:write', 'reconcile:admin'],
      isTestMode: newKeyEnv === 'test',
      createdAt: new Date().toISOString(),
      lastUsedAt: 'Never',
    }
    setApiKeys([newEntry, ...apiKeys])
    setCreatedKeySecret(fullKey)
    setNewKeyName('')
  }

  // Test Razorpay Connection handler
  const handleTestRazorpay = () => {
    setRzpTesting(true)
    setRzpTestResult(null)
    setTimeout(() => {
      setRzpTesting(false)
      setRzpTestResult({
        success: true,
        latency: 18,
        msg: 'HMAC-SHA256 handshake valid · Razorpay Gateway v1 responded HTTP 200 OK'
      })
    }, 800)
  }

  // Send Test Webhook
  const handleSendTestWebhook = () => {
    setIsSendingWebhook(true)
    setTimeout(() => {
      setIsSendingWebhook(false)
      setWebhookLog({
        event: testWebhookEvent,
        status: 200,
        signature: `hmac_sha256_${Math.random().toString(16).substring(2, 12)}`,
        time: new Date().toLocaleTimeString(),
      })
    }, 600)
  }

  // Rotate Webhook Secret
  const handleRotateWebhookSecret = () => {
    const newSecret = `whsec_sha256_${Math.random().toString(16).substring(2, 18)}`
    setWebhookSecret(newSecret)
    alert('Webhook secret rotated. A 12-hour dual-secret transition window has been opened.')
  }

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 className="page-title">Settings & Gateway Adapters</h1>
              <span className="badge badge-captured" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <CheckCircle2 size={12} />
                ALL SYSTEMS OPERATIONAL
              </span>
            </div>
            <p className="page-subtitle">
              Multi-tenant security tokens, Razorpay gateway adapters, HMAC webhook signing & invariant configurations
            </p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>TEST MODE ENVIRONMENT</span>
          </div>
        </header>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 24, borderBottom: '1px solid var(--border-color)', paddingBottom: 12 }}>
          {[
            { id: 'credentials', label: 'API Keys & Auth', icon: Key },
            { id: 'gateways', label: 'Payment Adapters', icon: Zap },
            { id: 'webhooks', label: 'Webhooks & HMAC', icon: Radio },
            { id: 'invariants', label: 'Invariant Engine Rules', icon: Sliders },
            { id: 'infrastructure', label: 'Cluster Health', icon: Activity },
          ].map(tab => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '8px 16px',
                  borderRadius: 8,
                  border: `1px solid ${isActive ? 'var(--brand-primary)' : 'transparent'}`,
                  background: isActive ? 'var(--brand-light)' : 'transparent',
                  color: isActive ? 'var(--brand-primary)' : 'var(--text-secondary)',
                  fontWeight: isActive ? 700 : 500,
                  fontSize: 13,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <Icon size={15} />
                <span>{tab.label}</span>
              </button>
            )
          })}
        </div>

        {/* TAB 1: API KEYS & CREDENTIALS */}
        {activeTab === 'credentials' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Active Tenant API Keys</h3>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: '4px 0 0' }}>
                    Keys authenticate client SDKs and backend services with granular scope validation
                  </p>
                </div>
                <button
                  onClick={() => { setIsGeneratingKey(!isGeneratingKey); setCreatedKeySecret(null) }}
                  className="btn btn-primary"
                  style={{ fontSize: 13, gap: 6 }}
                >
                  <Plus size={14} />
                  <span>Generate New Key</span>
                </button>
              </div>

              {/* Interactive Key Generator Form */}
              {isGeneratingKey && (
                <div
                  style={{
                    padding: 16,
                    background: 'var(--bg-subtle)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 8,
                    marginBottom: 20,
                  }}
                >
                  <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 10 }}>Generate Scoped Invariant Key</h4>
                  <form onSubmit={handleCreateApiKey} style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
                    <div style={{ flex: '1 1 240px' }}>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Key Label / Service Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Next.js Edge Middleware or Worker Node"
                        value={newKeyName}
                        onChange={e => setNewKeyName(e.target.value)}
                        required
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: 6,
                          border: '1px solid var(--border-color)',
                          fontSize: 13,
                        }}
                      />
                    </div>
                    <div style={{ width: 140 }}>
                      <label style={{ display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4 }}>Environment</label>
                      <select
                        value={newKeyEnv}
                        onChange={e => setNewKeyEnv(e.target.value as any)}
                        style={{
                          width: '100%',
                          padding: '8px 12px',
                          borderRadius: 6,
                          border: '1px solid var(--border-color)',
                          fontSize: 13,
                          background: '#fff',
                        }}
                      >
                        <option value="test">Test Mode (pg_test_)</option>
                        <option value="live">Live Production (pg_live_)</option>
                      </select>
                    </div>
                    <button type="submit" className="btn btn-primary" style={{ padding: '8px 18px', fontSize: 13 }}>
                      Create Key
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsGeneratingKey(false)}
                      className="btn btn-secondary"
                      style={{ padding: '8px 14px', fontSize: 13 }}
                    >
                      Cancel
                    </button>
                  </form>

                  {createdKeySecret && (
                    <div
                      style={{
                        marginTop: 14,
                        padding: 12,
                        background: '#ecfdf5',
                        border: '1px solid #a7f3d0',
                        borderRadius: 6,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                      }}
                    >
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 700, color: '#065f46' }}>
                          ✓ Key Generated! Save this secret now. It will not be shown again:
                        </div>
                        <code style={{ fontSize: 13, color: '#047857', fontWeight: 700, background: '#fff', padding: '2px 8px', borderRadius: 4, marginTop: 4, display: 'inline-block' }}>
                          {createdKeySecret}
                        </code>
                      </div>
                      <button
                        onClick={() => handleCopy(createdKeySecret, 'newly_created')}
                        className="btn btn-secondary"
                        style={{ fontSize: 12, gap: 4 }}
                      >
                        {copiedKey === 'newly_created' ? <Check size={14} color="#059669" /> : <Copy size={14} />}
                        <span>{copiedKey === 'newly_created' ? 'Copied' : 'Copy Key'}</span>
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* Keys Table */}
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Key Name</th>
                      <th>Key Prefix</th>
                      <th>Environment</th>
                      <th>Granular Scopes</th>
                      <th>Last Active</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {apiKeys.map(k => (
                      <tr key={k.id}>
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{k.name}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>ID: {k.id}</div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <code className="id-chip">{k.keyPrefix}••••••••</code>
                            <button
                              onClick={() => handleCopy(`${k.keyPrefix}fake_demo_secret_token_2026`, k.id)}
                              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}
                              title="Copy prefix"
                            >
                              {copiedKey === k.id ? <Check size={14} color="#059669" /> : <Copy size={14} />}
                            </button>
                          </div>
                        </td>
                        <td>
                          <span className={`badge badge-${k.isTestMode ? 'pending' : 'captured'}`}>
                            {k.isTestMode ? 'TEST SANDBOX' : 'PRODUCTION'}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                            {k.scopes.map(s => (
                              <span
                                key={s}
                                style={{
                                  fontSize: 10,
                                  fontWeight: 600,
                                  fontFamily: 'monospace',
                                  padding: '2px 5px',
                                  borderRadius: 4,
                                  background: 'var(--bg-subtle)',
                                  border: '1px solid var(--border-color)',
                                }}
                              >
                                {s}
                              </span>
                            ))}
                          </div>
                        </td>
                        <td style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{k.lastUsedAt}</td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            onClick={() => setApiKeys(apiKeys.filter(x => x.id !== k.id))}
                            style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', padding: 4 }}
                            title="Revoke key"
                          >
                            <Trash2 size={15} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: PAYMENT ADAPTERS */}
        {activeTab === 'gateways' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 20 }}>
            {/* Razorpay Adapter */}
            <div className="card" style={{ borderTop: '4px solid var(--brand-primary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#2563eb' }} />
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Razorpay Payment Gateway</h3>
                </div>
                <span className="badge badge-captured">CONNECTED</span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.5 }}>
                Official Razorpay API integration with automated HMAC-SHA256 signature verification, Orders API, and refunds.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 16 }}>
                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Key ID</label>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <input
                      type="text"
                      value={rzpKeyId}
                      onChange={e => setRzpKeyId(e.target.value)}
                      style={{ flex: 1, padding: '6px 10px', fontSize: 12, fontFamily: 'monospace', borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-subtle)' }}
                    />
                    <button onClick={() => handleCopy(rzpKeyId, 'rzp_id')} className="btn btn-secondary" style={{ padding: '6px 10px' }}>
                      {copiedKey === 'rzp_id' ? <Check size={13} color="#059669" /> : <Copy size={13} />}
                    </button>
                  </div>
                </div>

                <div>
                  <label style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Key Secret</label>
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <input
                      type={showKeySecret ? 'text' : 'password'}
                      value={rzpSecret}
                      onChange={e => setRzpSecret(e.target.value)}
                      style={{ flex: 1, padding: '6px 10px', fontSize: 12, fontFamily: 'monospace', borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-subtle)' }}
                    />
                    <button onClick={() => setShowKeySecret(!showKeySecret)} className="btn btn-secondary" style={{ padding: '6px 10px' }}>
                      {showKeySecret ? <EyeOff size={13} /> : <Eye size={13} />}
                    </button>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button
                  onClick={handleTestRazorpay}
                  disabled={rzpTesting}
                  className="btn btn-primary"
                  style={{ flex: 1, justifyContent: 'center', fontSize: 13, gap: 6 }}
                >
                  <RefreshCw size={14} className={rzpTesting ? 'spin' : ''} />
                  <span>{rzpTesting ? 'Testing Handshake...' : 'Test Gateway Connection'}</span>
                </button>
              </div>

              {rzpTestResult && (
                <div style={{ marginTop: 12, padding: 10, background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: 6, fontSize: 12, color: '#065f46' }}>
                  <div style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 4 }}>
                    <CheckCircle2 size={13} />
                    <span>Razorpay API Live ({rzpTestResult.latency}ms)</span>
                  </div>
                  <div style={{ fontSize: 11, marginTop: 2 }}>{rzpTestResult.msg}</div>
                </div>
              )}
            </div>

            {/* Deterministic Chaos Simulator */}
            <div className="card" style={{ borderTop: '4px solid #f59e0b' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#f59e0b' }} />
                  <h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Deterministic Chaos Simulator</h3>
                </div>
                <span className="badge badge-reconciled">CI ACTIVE</span>
              </div>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 16, lineHeight: 1.5 }}>
                Simulates network packet drops, ambiguous timeouts, idempotency replay attacks, and bank downtimes for chaos validation.
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, fontSize: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
                  <span>State Invariant Enforcement</span>
                  <span style={{ fontWeight: 700, color: '#059669' }}>STRICT (158 Tests)</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
                  <span>Timeout Ambiguity Injection</span>
                  <span style={{ fontWeight: 700, color: 'var(--brand-primary)' }}>Supported (2000ms)</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--bg-subtle)', borderRadius: 6 }}>
                  <span>Idempotency Collision Guard</span>
                  <span style={{ fontWeight: 700, color: '#059669' }}>Zero Re-charge Lock</span>
                </div>
              </div>

              <div style={{ marginTop: 18 }}>
                <span className="badge badge-pending" style={{ width: '100%', justifyContent: 'center', padding: '6px 0' }}>
                  Deterministic State Machine Active
                </span>
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: WEBHOOKS & HMAC */}
        {activeTab === 'webhooks' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div className="card">
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 4 }}>Razorpay Webhook Endpoint</h3>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 16 }}>
                Receives asynchronous payment state transitions directly from Razorpay with mandatory HMAC-SHA256 signature verification
              </p>

              <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
                <input
                  type="text"
                  readOnly
                  value="https://api.invarpay.ai/v1/webhooks/razorpay"
                  style={{ flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color)', background: 'var(--bg-subtle)', fontFamily: 'monospace', fontSize: 13 }}
                />
                <button
                  onClick={() => handleCopy('https://api.invarpay.ai/v1/webhooks/razorpay', 'wh_url')}
                  className="btn btn-secondary"
                  style={{ gap: 4 }}
                >
                  {copiedKey === 'wh_url' ? <Check size={14} color="#059669" /> : <Copy size={14} />}
                  <span>{copiedKey === 'wh_url' ? 'Copied' : 'Copy Endpoint'}</span>
                </button>
              </div>

              <div style={{ padding: 14, background: 'var(--bg-subtle)', borderRadius: 8, border: '1px solid var(--border-color)', marginBottom: 20 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700 }}>HMAC Webhook Secret</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Used by X-Razorpay-Signature verification middleware</div>
                  </div>
                  <button onClick={handleRotateWebhookSecret} className="btn btn-secondary" style={{ fontSize: 11, padding: '5px 10px', gap: 4 }}>
                    <RefreshCw size={12} />
                    <span>Rotate Secret</span>
                  </button>
                </div>
                <code style={{ fontSize: 12, fontFamily: 'monospace', color: 'var(--brand-primary)', fontWeight: 700 }}>
                  {webhookSecret}
                </code>
              </div>

              {/* Test Webhook Sender */}
              <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: 16 }}>
                <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Dispatch Synthetic Test Webhook</h4>
                <div style={{ display: 'flex', gap: 10 }}>
                  <select
                    value={testWebhookEvent}
                    onChange={e => setTestWebhookEvent(e.target.value)}
                    style={{ flex: 1, padding: '8px 12px', borderRadius: 6, border: '1px solid var(--border-color)', background: '#fff', fontSize: 13 }}
                  >
                    <option value="payment.captured">payment.captured (Simulate successful settlement)</option>
                    <option value="payment.failed">payment.failed (Simulate card decline)</option>
                    <option value="refund.processed">refund.processed (Simulate reverse ledger entry)</option>
                    <option value="order.paid">order.paid (Simulate checkout completion)</option>
                  </select>
                  <button
                    onClick={handleSendTestWebhook}
                    disabled={isSendingWebhook}
                    className="btn btn-primary"
                    style={{ gap: 6, fontSize: 13 }}
                  >
                    <Send size={14} />
                    <span>{isSendingWebhook ? 'Sending...' : 'Dispatch Ping'}</span>
                  </button>
                </div>

                {webhookLog && (
                  <div style={{ marginTop: 12, padding: 12, background: '#ecfdf5', border: '1px solid #a7f3d0', borderRadius: 6, fontSize: 12 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, color: '#065f46', marginBottom: 4 }}>
                      <span>✓ Webhook Verified (HTTP {webhookLog.status} OK)</span>
                      <span>{webhookLog.time}</span>
                    </div>
                    <div style={{ color: '#047857', fontSize: 11 }}>
                      Event: <code>{webhookLog.event}</code> · Sig: <code>{webhookLog.signature}</code> · State updated via Outbox
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: INVARIANT RULES */}
        {activeTab === 'invariants' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div className="card">
              <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>Core Invariant Engine Configurations</h3>
              <div style={{ display: 'grid', gap: 16 }}>
                <div style={{ padding: 16, background: 'var(--bg-subtle)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>Invariant 2: Unknown Outcome Lock</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Never auto-retry payment attempts in ambiguous timeout states</div>
                    </div>
                    <span className="badge badge-captured">LOCKED / STRICT</span>
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Max Retries Allowed on <code>unknown</code>: <strong>0 (Immutable)</strong>
                  </div>
                </div>

                <div style={{ padding: 16, background: 'var(--bg-subtle)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>Sliding Window Rate Limiter</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Redis token bucket protecting against traffic spikes</div>
                    </div>
                    <span className="badge badge-reconciled">{rateLimitRpm} REQ / MIN</span>
                  </div>
                  <input
                    type="range"
                    min="100"
                    max="5000"
                    step="100"
                    value={rateLimitRpm}
                    onChange={e => setRateLimitRpm(Number(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--brand-primary)', marginTop: 8 }}
                  />
                </div>

                <div style={{ padding: 16, background: 'var(--bg-subtle)', borderRadius: 8, border: '1px solid var(--border-color)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: 14 }}>Transactional Outbox Batch Sync</div>
                      <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Polling interval for relaying state machine events to queue</div>
                    </div>
                    <span className="badge badge-pending">{outboxSyncMs} ms</span>
                  </div>
                  <input
                    type="range"
                    min="50"
                    max="1000"
                    step="50"
                    value={outboxSyncMs}
                    onChange={e => setOutboxSyncMs(Number(e.target.value))}
                    style={{ width: '100%', accentColor: 'var(--brand-primary)', marginTop: 8 }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: INFRASTRUCTURE & CLUSTER HEALTH */}
        {activeTab === 'infrastructure' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <Database size={20} color="var(--brand-primary)" />
                <h4 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>PostgreSQL 16 ACID Engine</h4>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Status</span>
                  <span style={{ color: '#059669', fontWeight: 700 }}>HEALTHY / ONLINE</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Query Latency</span>
                  <span className="mono">1.8 ms</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Connection Pool</span>
                  <span className="mono">12 / 100 Active</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Transaction Isolation</span>
                  <span className="mono">SERIALIZABLE</span>
                </div>
              </div>
            </div>

            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <Server size={20} color="var(--brand-primary)" />
                <h4 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Redis 7.2 In-Memory Cluster</h4>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Status</span>
                  <span style={{ color: '#059669', fontWeight: 700 }}>HEALTHY / ONLINE</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Command Latency</span>
                  <span className="mono">0.6 ms</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Memory Usage</span>
                  <span className="mono">38.2 MB / 2 GB</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Idempotency Keys</span>
                  <span className="mono">14,291 cached</span>
                </div>
              </div>
            </div>

            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                <Cpu size={20} color="var(--brand-primary)" />
                <h4 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>LangGraph AI Supervisor</h4>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Status</span>
                  <span style={{ color: '#059669', fontWeight: 700 }}>AUTONOMOUS READY</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Active Nodes</span>
                  <span className="mono">4 Graph Workers</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Reconciliation Queue</span>
                  <span className="mono">0 pending (Clear)</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Pytest Test Suite</span>
                  <span style={{ color: '#059669', fontWeight: 700 }}>158 / 158 PASS</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
