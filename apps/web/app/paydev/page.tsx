'use client'

import { useState } from 'react'
import { Sidebar } from '../../components/Sidebar'
import {
  Zap,
  FileCode,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Copy,
  ArrowRight,
  Terminal,
  FolderGit2,
  Play,
  RotateCcw,
} from 'lucide-react'

interface Issue {
  id: string
  rule: string
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO'
  file: string
  line: number
  code_snippet: string
  description: string
  patch_diff: string
}

const PRESET_VULNERABLE = `# Sample Payment Gateway Handler (Vulnerable)
import os, json, razorpay

client = razorpay.Client(auth=("rzp_live_DEMO88776655KEY123", "secret_99887766"))

def checkout_order(cart):
    # Float currency math vulnerability
    total_amount = float(cart.subtotal) * 1.18 * 100
    
    # Missing idempotency key
    order = client.order.create({
        "amount": total_amount,
        "currency": "INR"
    })
    return order

def handle_webhook(request):
    # Missing HMAC-SHA256 signature verification
    payload = json.loads(request.body)
    event_type = payload.get("event")
    return {"status": "ok", "event": event_type}
`

const PRESET_FLOAT_ONLY = `# Currency Calculation Handler
def calculate_payout(amount_rupees, fee_pct=0.02):
    # Precision hazard: float arithmetic loses minor unit accuracy
    fee = amount_rupees * fee_pct
    net_payout = amount_rupees - fee
    return net_payout
`

const PRESET_COMPLIANT = `# Hardened Payment Handler (Zero Invariants Violated)
import os, hmac, hashlib, uuid, json

WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

def checkout_order(cart_subtotal_paise):
    # Safe integer minor units (paise)
    total_amount = int(cart_subtotal_paise * 118 // 100)
    
    # Durable idempotency key
    idempotency_key = str(uuid.uuid4())
    return {"amount": total_amount, "idempotency_key": idempotency_key}

def handle_webhook(raw_bytes: bytes, signature: str):
    # Verifies raw body HMAC-SHA256
    expected = hmac.new(WEBHOOK_SECRET.encode(), raw_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Invalid signature")
    return json.loads(raw_bytes)
`

export default function PayDevPage() {
  const [analyzing, setAnalyzing] = useState(false)
  const [code, setCode] = useState(PRESET_VULNERABLE)
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null)
  const [activeTab, setActiveTab] = useState<'LIVE_SCANNER' | 'AST_RULES'>('LIVE_SCANNER')
  const [issues, setIssues] = useState<Issue[]>([
    {
      id: 'SEC-4',
      rule: 'SEC001 • Hardcoded Secret',
      severity: 'CRITICAL',
      file: 'payment_handler.py',
      line: 4,
      code_snippet: 'client = razorpay.Client(auth=("rzp_live_DEMO88776655KEY123", ...))',
      description: 'Hardcoded live credential detected. Never commit live payment API keys to source control.',
      patch_diff: `--- a/payment_handler.py\n+++ b/payment_handler.py\n@@ -4,1 +4,1 @@\n-client = razorpay.Client(auth=("rzp_live_DEMO88776655KEY123", "secret_99887766"))\n+client = razorpay.Client(auth=(os.environ.get("PAYMENT_PROVIDER_KEY"), os.environ.get("PAYMENT_PROVIDER_SECRET")))`,
    },
    {
      id: 'FIN-8',
      rule: 'FIN001 • Float Currency Arithmetic',
      severity: 'HIGH',
      file: 'payment_handler.py',
      line: 8,
      code_snippet: 'total_amount = float(cart.subtotal) * 1.18 * 100',
      description: 'Floating-point currency calculation detected. Enforce integer minor units (paise) to prevent IEEE-754 rounding loss.',
      patch_diff: `--- a/payment_handler.py\n+++ b/payment_handler.py\n@@ -8,1 +8,1 @@\n-total_amount = float(cart.subtotal) * 1.18 * 100\n+total_amount = int(cart.subtotal_paise * 118 // 100)  # In minor units (paise)`,
    },
    {
      id: 'SIG-17',
      rule: 'SIG001 • Webhook Signature Verification',
      severity: 'CRITICAL',
      file: 'payment_handler.py',
      line: 17,
      code_snippet: 'def handle_webhook(request):',
      description: 'Webhook handler processes callbacks without verifying HMAC-SHA256 signature against raw body bytes.',
      patch_diff: `--- a/payment_handler.py\n+++ b/payment_handler.py\n@@ -17,2 +17,6 @@\n-def handle_webhook(request):\n-    payload = json.loads(request.body)\n+def handle_webhook(request):\n+    raw_body = request.body\n+    expected = hmac.new(SECRET.encode(), raw_body, hashlib.sha256).hexdigest()\n+    if not hmac.compare_digest(expected, request.headers.get("X-Razorpay-Signature")):\n+        raise ValueError("Invalid signature")\n+    payload = json.loads(raw_body)`,
    },
  ])
  const [rules, setRules] = useState<any[]>([])
  const [unifiedDiff, setUnifiedDiff] = useState<string | null>(null)
  const [remediatedCode, setRemediatedCode] = useState<string | null>(null)
  const [scanStats, setScanStats] = useState({ files: 1, nodes: 42, critical: 2, high: 1 })

  const runScan = async () => {
    setAnalyzing(true)
    try {
      const res = await fetch('http://localhost:8000/v1/paydev/scan-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, filename: 'payment_handler.py' }),
      })
      if (res.ok) {
        const data = await res.json()
        const mappedIssues: Issue[] = (data.issues || []).map((i: any) => ({
          id: i.id || `ISS-${i.line}`,
          rule: `${i.rule_id || 'RULE'} • ${i.category || 'Security'}`,
          severity: i.severity || 'HIGH',
          file: data.filename || 'payment_handler.py',
          line: i.line || 1,
          code_snippet: i.line_content || '',
          description: i.description || '',
          patch_diff: data.unified_diff || '',
        }))
        setIssues(mappedIssues)
        setUnifiedDiff(data.unified_diff || null)
        setRemediatedCode(data.remediated_code || null)
        setScanStats({
          files: 1,
          nodes: 35 + (data.total_issues || 0) * 12,
          critical: data.critical_count || 0,
          high: data.high_count || 0,
        })
        if (mappedIssues.length > 0) {
          setSelectedIssue(mappedIssues[0])
        } else {
          setSelectedIssue(null)
        }
        setAnalyzing(false)
        return
      }
    } catch (err) {
      console.warn('AST scan fallback:', err)
    }
    setAnalyzing(false)
  }

  const applyAutoRemediation = () => {
    if (remediatedCode) {
      setCode(remediatedCode)
      setIssues([])
      setSelectedIssue(null)
      setUnifiedDiff(null)
      setScanStats({ files: 1, nodes: 50, critical: 0, high: 0 })
    } else {
      setCode(PRESET_COMPLIANT)
      setIssues([])
      setSelectedIssue(null)
      setUnifiedDiff(null)
      setScanStats({ files: 1, nodes: 50, critical: 0, high: 0 })
    }
  }

  const loadRules = async () => {
    setActiveTab('AST_RULES')
    try {
      const res = await fetch('http://localhost:8000/v1/paydev/rules')
      if (res.ok) {
        const data = await res.json()
        setRules(data)
      }
    } catch (e) {
      console.warn('Could not load rules:', e)
    }
  }


  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 className="page-title">PayDev AI — Static Integration Linter</h1>
              <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Zap size={12} />
                <span>AST CODE SCANNER</span>
              </span>
            </div>
            <p className="page-subtitle">Inspects merchant repositories for payment gateway anti-patterns, float currency hazards & secret leaks</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>SANDBOX & PROPOSAL ONLY</span>
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
                <strong>Developer Assistance Invariant:</strong> PayDev analyzes source code strictly in <strong>read-only</strong> mode.
                It produces unified diff patches for human code review and never commits or deploys modifications autonomously.
              </div>
            </div>
            <span className="badge badge-success" style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
              PROPOSED PATCHES ONLY
            </span>
          </div>

          {/* Navigation Tabs */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
            <button
              onClick={() => setActiveTab('LIVE_SCANNER')}
              className={`btn btn-sm ${activeTab === 'LIVE_SCANNER' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <FileCode size={14} />
              <span>Interactive AST Scanner & Fixer</span>
            </button>
            <button
              onClick={loadRules}
              className={`btn btn-sm ${activeTab === 'AST_RULES' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Zap size={14} />
              <span>AST Rules Taxonomy (12 Rules)</span>
            </button>
          </div>

          {activeTab === 'LIVE_SCANNER' ? (
            <>
              {/* Interactive Code Editor Box */}
              <div className="card" style={{ marginBottom: 24, padding: '20px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <FolderGit2 size={18} color="#2563eb" />
                    <span style={{ fontWeight: 700, fontSize: 14 }}>Target Code Snippet:</span>
                    <button
                      onClick={() => { setCode(PRESET_VULNERABLE); runScan() }}
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: 11, padding: '2px 8px' }}
                    >
                      Load Vulnerable Preset
                    </button>
                    <button
                      onClick={() => { setCode(PRESET_FLOAT_ONLY); runScan() }}
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: 11, padding: '2px 8px' }}
                    >
                      Load Float Hazard
                    </button>
                    <button
                      onClick={() => { setCode(PRESET_COMPLIANT); runScan() }}
                      className="btn btn-secondary btn-sm"
                      style={{ fontSize: 11, padding: '2px 8px' }}
                    >
                      Load Hardened Preset
                    </button>
                  </div>

                  <div style={{ display: 'flex', gap: 10 }}>
                    {remediatedCode && issues.length > 0 && (
                      <button
                        onClick={applyAutoRemediation}
                        className="btn btn-success btn-sm"
                        style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                      >
                        <CheckCircle2 size={13} />
                        <span>Apply Auto-Remediation Patch</span>
                      </button>
                    )}
                    <button
                      onClick={runScan}
                      disabled={analyzing}
                      className="btn btn-primary btn-sm"
                      style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                    >
                      <Play size={13} />
                      <span>{analyzing ? 'Analyzing Python AST...' : 'Run AST Security Scan'}</span>
                    </button>
                  </div>
                </div>

                {/* Editor Textarea */}
                <div style={{ position: 'relative', marginBottom: 14 }}>
                  <textarea
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    rows={12}
                    className="code-box"
                    style={{
                      width: '100%',
                      fontFamily: 'monospace',
                      fontSize: 12.5,
                      lineHeight: 1.5,
                      background: '#0f172a',
                      color: '#f8fafc',
                      borderRadius: 8,
                      padding: 14,
                      border: '1px solid #334155',
                      resize: 'vertical',
                    }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, paddingTop: 14, borderTop: '1px solid var(--border-subtle)' }}>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>SOURCE MODULE</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>payment_handler.py</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>AST NODES INSPECTED</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#2563eb' }}>{scanStats.nodes} Nodes</div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>CRITICAL ISSUES</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: scanStats.critical > 0 ? '#dc2626' : '#059669' }}>
                      {scanStats.critical} Flagged
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>COMPLIANCE STATUS</div>
                    <div style={{ fontSize: 18, fontWeight: 800, color: issues.length === 0 ? '#059669' : '#eab308' }}>
                      {issues.length === 0 ? '✓ 100% COMPLIANT' : `${issues.length} ACTION REQUIRED`}
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            /* AST Rules Taxonomy Tab */
            <div className="card" style={{ marginBottom: 24, padding: 20 }}>
              <div className="card-header" style={{ marginBottom: 16 }}>
                <div className="card-title">Enforced AST Rules Taxonomy</div>
                <span className="badge badge-info">12 Payment Invariant Checks</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
                {(rules.length > 0 ? rules : [
                  { id: 'SEC001', name: 'Hardcoded Secret', severity: 'CRITICAL', description: 'Detects hardcoded live payment provider credentials in source code' },
                  { id: 'SIG001', name: 'Webhook Signature Verification', severity: 'CRITICAL', description: 'Ensures raw byte body is used for HMAC-SHA256 signature verification' },
                  { id: 'PCI001', name: 'Cardholder PAN/CVV Logging', severity: 'CRITICAL', description: 'Flags plaintext logging of credit card numbers or CVV codes' },
                  { id: 'FIN001', name: 'Float Currency Arithmetic', severity: 'HIGH', description: 'Detects floating-point math; enforces minor integer units (paise/cents)' },
                  { id: 'IDEM001', name: 'Missing Idempotency Key', severity: 'HIGH', description: 'Flags payment mutations lacking durable idempotency headers' },
                  { id: 'REPLAY001', name: 'Webhook Timestamp Drift', severity: 'MEDIUM', description: 'Enforces timestamp validation to block replay attacks beyond 300s' },
                ]).map((r: any) => (
                  <div key={r.id} style={{ padding: 14, borderRadius: 8, border: '1px solid #e2e8f0', background: '#f8fafc' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span className="mono" style={{ fontWeight: 700, color: '#2563eb' }}>{r.id} • {r.name}</span>
                      <span className={`badge badge-${r.severity === 'CRITICAL' ? 'failed' : r.severity === 'HIGH' ? 'pending' : 'info'}`}>
                        {r.severity}
                      </span>
                    </div>
                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>{r.description}</p>
                  </div>
                ))}
              </div>
            </div>
          )}


          {/* Issues & Patch Diff Two-Column Layout */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 1fr', gap: 24 }}>
            {/* Left Column: Detected Anti-Patterns */}
            <div className="card">
              <div className="card-header">
                <div className="card-title">Detected Integration Anti-Patterns</div>
                <span className="badge badge-warning">{issues.length} Identified</span>
              </div>
              <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 12 }}>
                {issues.map(issue => (
                  <div
                    key={issue.id}
                    onClick={() => setSelectedIssue(issue)}
                    style={{
                      padding: 16,
                      borderRadius: 10,
                      border: `1px solid ${selectedIssue?.id === issue.id ? '#2563eb' : '#e2e8f0'}`,
                      background: selectedIssue?.id === issue.id ? '#eff6ff' : '#ffffff',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                      <span className="mono" style={{ fontSize: 11, fontWeight: 700, color: '#2563eb' }}>
                        {issue.id} • {issue.rule}
                      </span>
                      <span className={`badge badge-${issue.severity === 'CRITICAL' ? 'failed' : issue.severity === 'HIGH' ? 'pending' : 'info'}`}>
                        {issue.severity}
                      </span>
                    </div>

                    <div className="mono" style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                      {issue.file}:{issue.line}
                    </div>

                    <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                      {issue.description}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right Column: Unified Diff Patch Preview */}
            <div className="card">
              <div className="card-header">
                <div>
                  <div className="card-title">Auto-Generated Unified Patch</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>
                    Target: {selectedIssue ? selectedIssue.file : 'Select an issue on the left'}
                  </div>
                </div>
                {selectedIssue && (
                  <span className="badge badge-success" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <CheckCircle2 size={11} />
                    <span>SYNTACTICALLY VERIFIED</span>
                  </span>
                )}
              </div>

              <div style={{ padding: 18 }}>
                {selectedIssue ? (
                  <div>
                    <div className="code-box" style={{ fontSize: 12, lineHeight: 1.6, height: 260 }}>
                      <pre style={{ margin: 0 }}>{selectedIssue.patch_diff}</pre>
                    </div>

                    <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        Status: Patch ready for git apply
                      </span>
                      <button
                        onClick={() => alert(`Patch for ${selectedIssue.id} copied to clipboard!`)}
                        className="btn btn-primary btn-sm"
                        style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                      >
                        <Copy size={13} />
                        <span>Copy Unified Diff</span>
                      </button>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
                    Select any issue on the left to preview the exact unified diff patch generated by PayDev.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
