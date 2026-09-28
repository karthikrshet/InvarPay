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

export default function PayDevPage() {
  const [analyzing, setAnalyzing] = useState(false)
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null)
  const [activeTab, setActiveTab] = useState<'ISSUES' | 'AST_RULES' | 'LIVE_SCANNER'>('ISSUES')

  const issues: Issue[] = [
    {
      id: 'ISS-001',
      rule: 'FLOAT_CURRENCY_ARITHMETIC',
      severity: 'HIGH',
      file: 'apps/merchant/services/checkout.py',
      line: 34,
      code_snippet: 'total_amount = float(cart.subtotal) * 1.18 * 100',
      description: 'Floating-point multiplication produces IEEE 754 precision loss. 149.99 * 1.18 * 100 evaluates to 17698.819999999998, causing ₹ 0.01 discrepancies in gateway capture calls.',
      patch_diff: `--- a/apps/merchant/services/checkout.py
+++ b/apps/merchant/services/checkout.py
@@ -34,1 +34,2 @@
-total_amount = float(cart.subtotal) * 1.18 * 100
+# Enforce integer minor units (paise) with math.ceil
+total_amount = int(cart.subtotal_paise * 118 // 100)`,
    },
    {
      id: 'ISS-002',
      rule: 'UNVERIFIED_WEBHOOK_SIGNATURE',
      severity: 'CRITICAL',
      file: 'apps/merchant/routers/webhooks.py',
      line: 18,
      code_snippet: 'event = json.loads(await request.body()) # Missing hmac.compare_digest',
      description: 'Webhook router processes payload without raw-body HMAC-SHA256 signature validation against X-Razorpay-Signature. Vulnerable to forged payment.captured events.',
      patch_diff: `--- a/apps/merchant/routers/webhooks.py
+++ b/apps/merchant/routers/webhooks.py
@@ -18,2 +18,6 @@
-event = json.loads(await request.body())
+raw_body = await request.body()
+signature = request.headers.get("X-Razorpay-Signature")
+expected = hmac.new(WEBHOOK_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
+if not hmac.compare_digest(signature, expected):
+    raise HTTPException(status_code=400, detail="Invalid signature")
+event = json.loads(raw_body)`,
    },
    {
      id: 'ISS-003',
      rule: 'HARDCODED_API_CREDENTIAL',
      severity: 'MEDIUM',
      file: 'apps/merchant/config.py',
      line: 12,
      code_snippet: 'RAZORPAY_KEY_ID = "rzp_test_1DP5mmOlF5G5ag"',
      description: 'Razorpay test key credentials detected in source file. Secrets should always be provisioned via environment variables or secret vaults.',
      patch_diff: `--- a/apps/merchant/config.py
+++ b/apps/merchant/config.py
@@ -12,1 +12,1 @@
-RAZORPAY_KEY_ID = "rzp_test_1DP5mmOlF5G5ag"
+RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID")`,
    },
  ]

  const runScan = () => {
    setAnalyzing(true)
    setTimeout(() => {
      setAnalyzing(false)
      setSelectedIssue(issues[0])
    }, 700)
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

          {/* Repository Scanner Box */}
          <div className="card" style={{ marginBottom: 24, padding: '20px 24px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14, flexWrap: 'wrap', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <FolderGit2 size={18} color="#2563eb" />
                <span style={{ fontWeight: 700, fontSize: 14 }}>Target Repository:</span>
                <span className="mono" style={{ background: '#f1f5f9', padding: '3px 8px', borderRadius: 4, fontSize: 12 }}>
                  d:\razorpay\payguard-ai
                </span>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
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

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, paddingTop: 14, borderTop: '1px solid var(--border-subtle)' }}>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>FILES ANALYZED</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: 'var(--text-primary)' }}>142 Files</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>AST NODES INSPECTED</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: '#2563eb' }}>18,490 Nodes</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>CRITICAL ISSUES</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: '#dc2626' }}>1 Flagged</div>
              </div>
              <div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>AUTO-FIX PATCHES</div>
                <div style={{ fontSize: 20, fontWeight: 800, color: '#059669' }}>3 Ready</div>
              </div>
            </div>
          </div>

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
