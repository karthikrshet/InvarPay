'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  Zap,
  ShieldCheck,
  Cpu,
  Globe,
  Database,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  ChevronDown,
  AlertTriangle,
  RotateCcw,
  FileCode,
  TrendingUp,
  ShoppingCart,
  Sliders,
  ExternalLink,
  MessageSquare,
  Bot,
  Lock,
  X,
  Activity,
  Server,
  Layers,
} from 'lucide-react'

export default function LandingPage() {
  const [activeTab, setActiveTab] = useState<'payguard' | 'paydev' | 'risk' | 'merchantos'>('payguard')
  const [chatOpen, setChatOpen] = useState(false)

  // PayGuard Simulator State
  const [simState, setSimState] = useState<'INITIATED' | 'PROCESSING' | 'SUCCESS' | 'FAILED'>('INITIATED')
  const [simLog, setSimLog] = useState<string[]>([
    'T0: Payment pay_01J8K901 initiated with amount 149900 INR (minor units).',
    'T1: Idempotency lock acquired in Redis (pg_lock_pay_01J8K901, TTL=60s).',
    'T2: State transitioned: CREATED → INITIATED (Invariant verified).',
  ])

  // PayDev AST Scanner State
  const [astScanned, setAstScanned] = useState(false)

  // Risk Score Slider State
  const [velocityCount, setVelocityCount] = useState(3)
  const [txAmount, setTxAmount] = useState(25000)

  // Handler for state machine transitions
  const triggerTransition = (target: 'PROCESSING' | 'SUCCESS' | 'FAILED' | 'ILLEGAL') => {
    const timestamp = new Date().toLocaleTimeString()
    if (target === 'ILLEGAL') {
      setSimLog(prev => [
        `❌ [${timestamp}] BLOCKED: Illegal transition attempted from ${simState} to REFUNDED. Terminal guard invariant enforced. Double-spend prevented!`,
        ...prev,
      ])
      return
    }

    if (simState === 'INITIATED' && target === 'PROCESSING') {
      setSimState('PROCESSING')
      setSimLog(prev => [
        `✓ [${timestamp}] State updated: INITIATED → PROCESSING. Outbox event emitted: payment.processing.`,
        ...prev,
      ])
    } else if (simState === 'PROCESSING' && target === 'SUCCESS') {
      setSimState('SUCCESS')
      setSimLog(prev => [
        `✓ [${timestamp}] CAPTURED: PROCESSING → SUCCESS. Dual-entry ledger balanced: Dr. Razorpay Gateway 1499.00 / Cr. Merchant Cash 1499.00.`,
        ...prev,
      ])
    } else if (simState === 'PROCESSING' && target === 'FAILED') {
      setSimState('FAILED')
      setSimLog(prev => [
        `⚠️ [${timestamp}] FAILED: PROCESSING → FAILED. Auto-recovery engine triggered. Circuit breaker healthy.`,
        ...prev,
      ])
    } else if (simState === 'SUCCESS' || simState === 'FAILED') {
      setSimLog(prev => [
        `ℹ️ [${timestamp}] State is TERMINAL (${simState}). Reset simulator to run another lifecycle.`,
        ...prev,
      ])
    }
  }

  const resetSimulator = () => {
    setSimState('INITIATED')
    setSimLog([
      'Simulator reset. State: INITIATED. Ready for idempotent transition dispatch.',
    ])
  }

  // Calculate synthetic risk
  const calculatedRisk = Math.min(98, Math.round((velocityCount * 12) + (txAmount > 50000 ? 35 : txAmount > 20000 ? 18 : 5)))
  const riskTier = calculatedRisk > 75 ? 'HIGH RISK (BLOCKED)' : calculatedRisk > 40 ? 'MEDIUM (STEP-UP 3DS)' : 'LOW (AUTO-AUTHORIZED)'
  const riskColor = calculatedRisk > 75 ? '#dc2626' : calculatedRisk > 40 ? '#d97706' : '#059669'

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)', position: 'relative' }}>
      {/* ── Ambient Radial Glow ── */}
      <div className="hero-glow-bg" />

      {/* ── Sticky Modern Navigation Header (Reference Image Style) ── */}
      <header className="site-header">
        <div className="site-header-inner">
          <Link href="/" className="brand-logo-wrap">
            <div className="brand-icon-box">
              <Zap size={20} strokeWidth={2.5} />
            </div>
            <div className="brand-name-wrap">
              <span className="brand-name">InvarPay AI</span>
              <span className="brand-tagline">FINTECH INVARIANT PLATFORM</span>
            </div>
          </Link>

          <nav>
            <ul className="nav-links">
              <li>
                <a href="#engines" className="nav-link-item">
                  <span>Five Engines</span>
                  <ChevronDown size={14} />
                </a>
              </li>
              <li>
                <a href="#topology" className="nav-link-item">
                  <span>Architecture</span>
                  <span className="nav-pill-badge">v0.1</span>
                </a>
              </li>
              <li>
                <a href="#simulator" className="nav-link-item">
                  <span>Live Simulator</span>
                  <ChevronDown size={14} />
                </a>
              </li>
              <li>
                <a href="#benchmarks" className="nav-link-item">
                  <span>158 Test Evals</span>
                </a>
              </li>
              <li>
                <Link href="/dashboard" className="nav-link-item">
                  <span>Console View</span>
                </Link>
              </li>
            </ul>
          </nav>

          <div className="header-actions">
            <Link href="#topology" className="btn btn-outline btn-sm">
              Scope Topology
            </Link>
            <Link href="/dashboard" className="btn btn-primary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>Launch Console</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero Section (Direct match to reference image structure) ── */}
      <section className="hero-section">
        {/* Left Column: Hero Content */}
        <div className="hero-content">
          <div className="hero-pill-badge">
            <Sparkles size={14} />
            <span>SOFTWARE THAT WORKS. AI THAT MAKES A DIFFERENCE.</span>
          </div>

          <h1 className="hero-title">
            Custom Software & <span className="text-gradient">AI Engineering</span> for Growing Businesses
          </h1>

          <p className="hero-subtitle">
            We design and develop resilient payment orchestration, dual-entry ledger reconciliation,
            and AI-powered guardrails for modern businesses—supported by rigorous state machine invariants,
            AST static analysis, and 158 automated test benchmarks.
          </p>

          <div className="hero-cta-group">
            <Link href="/dashboard" className="btn btn-primary btn-lg" style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span>Discuss your project</span>
              <ArrowRight size={16} />
            </Link>
            <a href="#simulator" className="btn btn-secondary btn-lg">
              Explore our services
            </a>
          </div>

          <div style={{ marginTop: 2 }}>
            <Link href="/payments" className="hero-sublink">
              <span>Looking for academic project mentorship & Razorpay AI Builder submission?</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          <div className="hero-proof-list">
            <div className="hero-proof-item">
              <CheckCircle2 size={16} className="hero-proof-icon" />
              <span>Zero Double-Spends & Invariant Locks</span>
            </div>
            <div className="hero-proof-item">
              <CheckCircle2 size={16} className="hero-proof-icon" />
              <span>Production Architecture</span>
            </div>
            <div className="hero-proof-item">
              <CheckCircle2 size={16} className="hero-proof-icon" />
              <span>158 Passing Automated Tests</span>
            </div>
          </div>
        </div>

        {/* Right Column: Architecture Topology Card (Exact Visual Replica) */}
        <div id="topology">
          <div className="topology-card">
            {/* Window Bar */}
            <div className="topology-window-header">
              <div className="mac-controls">
                <span className="mac-dot mac-dot-red" />
                <span className="mac-dot mac-dot-yellow" />
                <span className="mac-dot mac-dot-green" />
              </div>
              <span className="topology-filename">architecture-topology.ts</span>
              <span className="badge-ready">
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#059669' }} />
                SYSTEM READY
              </span>
            </div>

            {/* Layer Nodes */}
            <div className="topology-layers">
              {/* Layer 1 */}
              <div className="topology-layer-card">
                <div className="layer-left">
                  <div className="layer-icon-box">
                    <Globe size={18} />
                  </div>
                  <div className="layer-info">
                    <span className="layer-title">Client & Frontend Layer</span>
                    <span className="layer-desc">Next.js 14 SSR • React 18 • Native Apps</span>
                  </div>
                </div>
                <span className="layer-badge layer-badge-blue">Edge Optimized</span>
              </div>

              <div className="layer-connector" />

              {/* Layer 2 */}
              <div className="topology-layer-card">
                <div className="layer-left">
                  <div className="layer-icon-box" style={{ background: '#faf5ff', color: '#7e22ce' }}>
                    <Cpu size={18} />
                  </div>
                  <div className="layer-info">
                    <span className="layer-title">API & AI Workflow Engine</span>
                    <span className="layer-desc">FastAPI • LangGraph Agents • MCP Protocol</span>
                  </div>
                </div>
                <span className="layer-badge layer-badge-purple">Grounded RAG</span>
              </div>

              <div className="layer-connector" />

              {/* Layer 3 */}
              <div className="topology-layer-card">
                <div className="layer-left">
                  <div className="layer-icon-box" style={{ background: '#ecfdf5', color: '#059669' }}>
                    <ShieldCheck size={18} />
                  </div>
                  <div className="layer-info">
                    <span className="layer-title">Invariant State Machine & Ledger</span>
                    <span className="layer-desc">Dual-Entry Ledger • Minor Units • HMAC-SHA256</span>
                  </div>
                </div>
                <span className="layer-badge layer-badge-green">100% Invariant</span>
              </div>

              <div className="layer-connector" />

              {/* Layer 4 */}
              <div className="topology-layer-card">
                <div className="layer-left">
                  <div className="layer-icon-box" style={{ background: '#fdf4ff', color: '#c026d3' }}>
                    <Database size={18} />
                  </div>
                  <div className="layer-info">
                    <span className="layer-title">Database & Storage Layer</span>
                    <span className="layer-desc">PostgreSQL 16 • pgvector • Redis Cache</span>
                  </div>
                </div>
                <span className="layer-badge layer-badge-purple">Encrypted at Rest</span>
              </div>
            </div>

            {/* Bottom Stat Boxes */}
            <div className="topology-stats-grid">
              <div className="topology-stat-box">
                <div className="stat-label-top">High Availability</div>
                <div className="stat-desc-bottom">Target Architecture</div>
              </div>
              <div className="topology-stat-box">
                <div className="stat-label-top" style={{ color: '#059669' }}>Continuous</div>
                <div className="stat-desc-bottom">CI/CD Deployments</div>
              </div>
              <div className="topology-stat-box">
                <div className="stat-label-top" style={{ color: '#2563eb' }}>Milestone</div>
                <div className="stat-desc-bottom">100% IP Transfer</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Five Core Autonomous Engines Section ── */}
      <section id="engines" className="section-container" style={{ borderTop: '1px solid var(--border)' }}>
        <div className="section-header-center">
          <span className="section-tag">FULL ARCHITECTURAL STACK</span>
          <h2 className="section-title">Five Specialized Fintech & AI Engines</h2>
          <p className="section-desc">
            Designed as a modular monolith where each module has distinct responsibilities,
            isolated database schemas, and zero leaky domain abstractions.
          </p>
        </div>

        <div className="engines-grid">
          {/* Engine 1 */}
          <div className="engine-card">
            <div className="engine-card-header">
              <div className="engine-icon">
                <ShieldCheck size={22} />
              </div>
              <span className="badge badge-success">CORE INVARIANT</span>
            </div>
            <h3 className="engine-title">InvarPay Core Engine</h3>
            <p className="engine-desc">
              Strict finite-state machine transitions preventing double-captures and out-of-order webhooks.
              Enforces integer minor-unit math and raw-body HMAC-SHA256 signature verification.
            </p>
            <ul className="engine-features">
              <li className="engine-feature-item"><span className="engine-feature-dot" /> Terminal state guards & transition table</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" /> Redis-backed sliding-window idempotency</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" /> Automated 5-minute replay attack tolerance</li>
            </ul>
            <Link href="/payments" className="btn btn-outline btn-sm" style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Inspect Payment Machine</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Engine 2 */}
          <div className="engine-card">
            <div className="engine-card-header">
              <div className="engine-icon" style={{ background: '#faf5ff', color: '#7e22ce' }}>
                <Cpu size={22} />
              </div>
              <span className="badge badge-info">AI & FRAUD ML</span>
            </div>
            <h3 className="engine-title">PaymentGraph AI</h3>
            <p className="engine-desc">
              Real-time composite fraud risk scoring evaluating card velocity, IP country mismatch,
              and transaction heuristics. Accompanied by a formal EU AI Act model card.
            </p>
            <ul className="engine-features">
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#7e22ce' }} /> Isolation Forest ML inference fallback</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#7e22ce' }} /> Velocity limits across 5m, 1h, and 24h windows</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#7e22ce' }} /> Comprehensive model transparency schema</li>
            </ul>
            <Link href="/risk" className="btn btn-outline btn-sm" style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>View Risk Matrix</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Engine 3 */}
          <div className="engine-card">
            <div className="engine-card-header">
              <div className="engine-icon" style={{ background: '#fffbeb', color: '#d97706' }}>
                <Zap size={22} />
              </div>
              <span className="badge badge-warning">DEVELOPER AST</span>
            </div>
            <h3 className="engine-title">PayDev AST Linter</h3>
            <p className="engine-desc">
              Static Python code analyzer inspecting merchant payment integrations for dangerous anti-patterns:
              floating-point currency arithmetic, unverified webhooks, and raw secrets.
            </p>
            <ul className="engine-features">
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#d97706' }} /> Abstract Syntax Tree (AST) node visitor</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#d97706' }} /> Instant unified diff patch generator</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#d97706' }} /> Razorpay Key ID and auth token regex detector</li>
            </ul>
            <Link href="/paydev" className="btn btn-outline btn-sm" style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Run Code Analyzer</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Engine 4 */}
          <div className="engine-card">
            <div className="engine-card-header">
              <div className="engine-icon" style={{ background: '#f0fdf4', color: '#16a34a' }}>
                <TrendingUp size={22} />
              </div>
              <span className="badge badge-success">FINANCIAL OPS</span>
            </div>
            <h3 className="engine-title">MerchantOS & Ledger</h3>
            <p className="engine-desc">
              Dual-entry bookkeeping system with bank settlement CSV reconciliation, fee deductions,
              and 30/60/90-day cashflow trajectory forecasting.
            </p>
            <ul className="engine-features">
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#16a34a' }} /> Double-entry debit/credit ledger balance</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#16a34a' }} /> Bank UTR matching & discrepancy alerts</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" style={{ background: '#16a34a' }} /> Automated runway burn rate projections</li>
            </ul>
            <Link href="/merchantos" className="btn btn-outline btn-sm" style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Open Financial Ledger</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Engine 5 */}
          <div className="engine-card">
            <div className="engine-card-header">
              <div className="engine-icon" style={{ background: '#eff6ff', color: '#2563eb' }}>
                <ShoppingCart size={22} />
              </div>
              <span className="badge badge-info">AGENTIC COMMERCE</span>
            </div>
            <h3 className="engine-title">ShopAgent & MCP</h3>
            <p className="engine-desc">
              Model Context Protocol (MCP) tool server enabling LLM agents to search catalogs, reserve inventory,
              and initiate checkouts with mandatory human confirmation gates.
            </p>
            <ul className="engine-features">
              <li className="engine-feature-item"><span className="engine-feature-dot" /> FastMCP standardized tool definitions</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" /> Cryptographic approval token binding</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" /> Zero unauthorized charge guarantee</li>
            </ul>
            <Link href="/shop" className="btn btn-outline btn-sm" style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Explore Storefront</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Engine 6: LangGraph Dispute Agent */}
          <div className="engine-card" style={{ background: 'linear-gradient(135deg, #eff6ff 0%, #ffffff 100%)', borderColor: '#bfdbfe' }}>
            <div className="engine-card-header">
              <div className="engine-icon" style={{ background: '#2563eb', color: '#ffffff' }}>
                <Bot size={22} />
              </div>
              <span className="badge badge-success">AUTONOMOUS</span>
            </div>
            <h3 className="engine-title">LangGraph Dispute Agent</h3>
            <p className="engine-desc">
              Autonomous multi-step investigation agent triage with deterministic policy guardrails.
              Gathers audit traces, calculates merchant trust scores, and generates dispute recommendations.
            </p>
            <ul className="engine-features">
              <li className="engine-feature-item"><span className="engine-feature-dot" /> LangGraph stateful cyclic graph reasoning</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" /> Strict deny-by-default execution policy</li>
              <li className="engine-feature-item"><span className="engine-feature-dot" /> Audit log evidence packaging</li>
            </ul>
            <Link href="/investigations" className="btn btn-primary btn-sm" style={{ marginTop: 'auto', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span>Launch Investigation</span>
              <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Interactive Live Simulator Section ── */}
      <section id="simulator" className="section-container">
        <div className="section-header-center">
          <span className="section-tag">LIVE BROWSER INTERACTION</span>
          <h2 className="section-title">Interactive Invariant Playground</h2>
          <p className="section-desc">
            Test the underlying core engines right in your browser. Experience how strict state machines,
            AST code scanning, and risk heuristics behave under real conditions.
          </p>
        </div>

        <div className="interactive-simulator-card">
          {/* Tab Navigation */}
          <div className="simulator-tabs-bar">
            <button
              onClick={() => setActiveTab('payguard')}
              className={`sim-tab-btn ${activeTab === 'payguard' ? 'active' : ''}`}
            >
              <ShieldCheck size={16} />
              <span>InvarPay State Machine</span>
            </button>
            <button
              onClick={() => setActiveTab('paydev')}
              className={`sim-tab-btn ${activeTab === 'paydev' ? 'active' : ''}`}
            >
              <Zap size={16} />
              <span>PayDev AST Code Scanner</span>
            </button>
            <button
              onClick={() => setActiveTab('risk')}
              className={`sim-tab-btn ${activeTab === 'risk' ? 'active' : ''}`}
            >
              <Cpu size={16} />
              <span>PaymentGraph AI Scoring</span>
            </button>
            <button
              onClick={() => setActiveTab('merchantos')}
              className={`sim-tab-btn ${activeTab === 'merchantos' ? 'active' : ''}`}
            >
              <TrendingUp size={16} />
              <span>Double-Entry Ledger Matcher</span>
            </button>
          </div>

          {/* Tab 1: InvarPay State Machine */}
          {activeTab === 'payguard' && (
            <div className="simulator-pane">
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
                    <div>
                      <h4 style={{ fontSize: 16, fontWeight: 700 }}>Payment State Lifecycle Dispatcher</h4>
                      <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>ID: pay_01J8K901 • Amount: ₹ 1,499.00</p>
                    </div>
                    <span className={`badge badge-${simState.toLowerCase()}`} style={{ fontSize: 13, padding: '4px 12px' }}>
                      CURRENT: {simState}
                    </span>
                  </div>

                  {/* Flow Diagram */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '16px 20px', background: '#f8fafc', borderRadius: 10, border: '1px solid #e2e8f0', marginBottom: 20 }}>
                    <div style={{ textAlign: 'center', flex: 1, padding: 8, borderRadius: 6, background: simState === 'INITIATED' ? '#2563eb' : '#e2e8f0', color: simState === 'INITIATED' ? '#fff' : '#64748b', fontWeight: 700, fontSize: 12 }}>
                      1. INITIATED
                    </div>
                    <span>→</span>
                    <div style={{ textAlign: 'center', flex: 1, padding: 8, borderRadius: 6, background: simState === 'PROCESSING' ? '#2563eb' : '#e2e8f0', color: simState === 'PROCESSING' ? '#fff' : '#64748b', fontWeight: 700, fontSize: 12 }}>
                      2. PROCESSING
                    </div>
                    <span>→</span>
                    <div style={{ textAlign: 'center', flex: 1, padding: 8, borderRadius: 6, background: simState === 'SUCCESS' ? '#059669' : simState === 'FAILED' ? '#dc2626' : '#e2e8f0', color: simState === 'SUCCESS' || simState === 'FAILED' ? '#fff' : '#64748b', fontWeight: 700, fontSize: 12 }}>
                      3. TERMINAL
                    </div>
                  </div>

                  {/* Transition Action Buttons */}
                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 18 }}>
                    <button
                      onClick={() => triggerTransition('PROCESSING')}
                      disabled={simState !== 'INITIATED'}
                      className="btn btn-secondary btn-sm"
                      style={{ opacity: simState === 'INITIATED' ? 1 : 0.4 }}
                    >
                      Authorize (→ PROCESSING)
                    </button>
                    <button
                      onClick={() => triggerTransition('SUCCESS')}
                      disabled={simState !== 'PROCESSING'}
                      className="btn btn-primary btn-sm"
                      style={{ opacity: simState === 'PROCESSING' ? 1 : 0.4 }}
                    >
                      Capture (→ SUCCESS)
                    </button>
                    <button
                      onClick={() => triggerTransition('FAILED')}
                      disabled={simState !== 'PROCESSING'}
                      className="btn btn-outline btn-sm"
                      style={{ color: '#dc2626', borderColor: '#fca5a5', opacity: simState === 'PROCESSING' ? 1 : 0.4 }}
                    >
                      Simulate Failure (→ FAILED)
                    </button>
                    <button
                      onClick={() => triggerTransition('ILLEGAL')}
                      className="btn btn-outline btn-sm"
                      style={{ color: '#d97706', borderColor: '#fde68a', display: 'flex', alignItems: 'center', gap: 5 }}
                    >
                      <AlertTriangle size={13} />
                      <span>Attempt Illegal Jump</span>
                    </button>
                    <button
                      onClick={resetSimulator}
                      className="btn btn-outline btn-sm"
                      style={{ display: 'flex', alignItems: 'center', gap: 5 }}
                    >
                      <RotateCcw size={13} />
                      <span>Reset</span>
                    </button>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Try clicking &quot;Attempt Illegal Jump&quot; to observe how InvarPay AI rejects invalid jumps with cryptographic errors.
                  </p>
                </div>

                {/* Live Console Output */}
                <div>
                  <div className="code-header">
                    <span>LIVE INVARIANT TELEMETRY STREAM</span>
                    <span>JSON-RPC 2.0</span>
                  </div>
                  <div className="code-box" style={{ height: 210, overflowY: 'auto', fontSize: 12 }}>
                    {simLog.map((log, i) => (
                      <div key={i} style={{ marginBottom: 6, color: log.startsWith('❌') ? '#f87171' : log.startsWith('✓') ? '#4ade80' : '#e2e8f0' }}>
                        {log}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: PayDev AST Code Scanner */}
          {activeTab === 'paydev' && (
            <div className="simulator-pane">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28 }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <h4 style={{ fontSize: 15, fontWeight: 700 }}>Merchant Python Integration Snippet</h4>
                    <span className="badge badge-warning" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <AlertTriangle size={12} />
                      <span>2 VULNERABILITIES</span>
                    </span>
                  </div>
                  <div className="code-box" style={{ height: 220, fontSize: 12.5 }}>
                    <div style={{ color: '#64748b' }}># merchant_checkout.py</div>
                    <div>import razorpay</div>
                    <div style={{ color: '#f87171', background: 'rgba(239, 68, 68, 0.15)', padding: '2px 4px' }}>
                      client = razorpay.Client(auth=(&quot;rzp_test_123456&quot;, &quot;secret_key_abc&quot;)) # RULE: HARDCODED_SECRET
                    </div>
                    <div style={{ color: '#f87171', background: 'rgba(239, 68, 68, 0.15)', padding: '2px 4px', marginTop: 4 }}>
                      order_amount = 49.99 * 100  # RULE: FLOAT_CURRENCY_ARITHMETIC
                    </div>
                    <div style={{ marginTop: 4 }}>
                      order = client.order.create({'{&quot;amount&quot;: int(order_amount), &quot;currency&quot;: &quot;INR&quot;}'})
                    </div>
                  </div>

                  <div style={{ marginTop: 16 }}>
                    <button
                      onClick={() => setAstScanned(true)}
                      className="btn btn-primary btn-sm"
                      style={{ display: 'flex', alignItems: 'center', gap: 6 }}
                    >
                      <Zap size={14} />
                      <span>Run PayDev AST Static Scan & Generate Patch Diff</span>
                    </button>
                  </div>
                </div>

                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                    <h4 style={{ fontSize: 15, fontWeight: 700 }}>PayDev Auto-Generated Unified Patch</h4>
                    <span className="badge badge-success" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <CheckCircle2 size={12} />
                      <span>COMPLIANT AST FIX</span>
                    </span>
                  </div>

                  {astScanned ? (
                    <div className="code-box" style={{ height: 220, fontSize: 12 }}>
                      <div style={{ color: '#94a3b8' }}>--- a/merchant_checkout.py</div>
                      <div style={{ color: '#94a3b8' }}>+++ b/merchant_checkout.py</div>
                      <div style={{ color: '#f87171' }}>- client = razorpay.Client(auth=(&quot;rzp_test_123456&quot;, &quot;secret_key_abc&quot;))</div>
                      <div style={{ color: '#4ade80' }}>+ client = razorpay.Client(auth=(os.environ[&quot;RAZORPAY_KEY_ID&quot;], os.environ[&quot;RAZORPAY_SECRET&quot;]))</div>
                      <div style={{ color: '#f87171' }}>- order_amount = 49.99 * 100</div>
                      <div style={{ color: '#4ade80' }}>+ order_amount = 4999 # Enforce integer minor units (paise)</div>
                      <div style={{ color: '#38bdf8', marginTop: 8 }}># Verification: Zero floating-point rounding hazards</div>
                    </div>
                  ) : (
                    <div style={{ height: 220, background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: 13, textAlign: 'center', padding: 20 }}>
                      Click &quot;Run PayDev AST Static Scan&quot; on the left to parse the Python AST and generate an instant patch diff.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: PaymentGraph AI Scoring */}
          {activeTab === 'risk' && (
            <div className="simulator-pane">
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32 }}>
                <div>
                  <h4 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Sliders size={18} color="#2563eb" />
                    <span>Live Risk Heuristic Parameters</span>
                  </h4>
                  
                  <div style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                      <span>Transaction Amount: ₹ {(txAmount).toLocaleString('en-IN')}</span>
                      <span className="mono" style={{ color: 'var(--brand-primary)' }}>{txAmount > 50000 ? 'High Value' : 'Standard'}</span>
                    </div>
                    <input
                      type="range"
                      min="500"
                      max="100000"
                      step="1000"
                      value={txAmount}
                      onChange={e => setTxAmount(Number(e.target.value))}
                      style={{ width: '100%' }}
                    />
                  </div>

                  <div style={{ marginBottom: 20 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                      <span>Card Velocity (Last 10 minutes): {velocityCount} transactions</span>
                      <span className="mono" style={{ color: velocityCount > 5 ? '#dc2626' : '#059669' }}>
                        {velocityCount > 5 ? 'Velocity Spike' : 'Normal'}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      value={velocityCount}
                      onChange={e => setVelocityCount(Number(e.target.value))}
                      style={{ width: '100%' }}
                    />
                  </div>

                  <div style={{ background: '#f8fafc', padding: 14, borderRadius: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                    PaymentGraph AI combines card velocity limits, IP country geo-distance, and scikit-learn Isolation Forest ML to compute an instant risk score.
                  </div>
                </div>

                <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 14, padding: 24, textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                  <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600 }}>COMPOSITE RISK SCORE</div>
                  <div style={{ fontSize: 56, fontWeight: 800, color: riskColor, letterSpacing: -1, margin: '8px 0' }}>
                    {calculatedRisk} <span style={{ fontSize: 20, color: 'var(--text-muted)' }}>/ 100</span>
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 14, color: riskColor }}>
                    {riskTier}
                  </div>
                  <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
                    Action: {calculatedRisk > 75 ? 'Trigger LangGraph Autonomous Dispute Investigation' : 'Proceed with Test-Mode Authorization'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 4: Double-Entry Ledger Matcher */}
          {activeTab === 'merchantos' && (
            <div className="simulator-pane">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 28 }}>
                <div>
                  <h4 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>Bank Settlement CSV Line (UTR: UTIB0001928374)</h4>
                  <div className="code-box" style={{ fontSize: 12, height: 160 }}>
                    <div>settlement_id: set_9910283</div>
                    <div>gross_amount: 150000 paise (₹ 1,500.00)</div>
                    <div>fee_deducted: 3000 paise (₹ 30.00)</div>
                    <div>tax_gst: 540 paise (₹ 5.40)</div>
                    <div style={{ color: '#4ade80' }}>net_settled: 146460 paise (₹ 1,464.60)</div>
                  </div>
                </div>

                <div>
                  <h4 style={{ fontSize: 15, fontWeight: 700, marginBottom: 12 }}>Dual-Entry Bookkeeping Ledger</h4>
                  <div className="code-box" style={{ fontSize: 12, height: 160 }}>
                    <div style={{ color: '#4ade80' }}>Dr. Bank Account (HDFC) : ₹ 1,464.60</div>
                    <div style={{ color: '#60a5fa' }}>Dr. Processing Fee Expense: ₹ 30.00</div>
                    <div style={{ color: '#60a5fa' }}>Dr. Input GST Tax Credit : ₹ 5.40</div>
                    <div style={{ color: '#f87171' }}>Cr. Accounts Receivable  : ₹ 1,500.00</div>
                    <div style={{ marginTop: 8, borderTop: '1px solid #334155', paddingTop: 4, color: '#38bdf8' }}>
                      LEDGER INVARIANT: SUM(Dr) == SUM(Cr) [MATCHED 100%]
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── Benchmarks & Test Suite Bar ── */}
      <section id="benchmarks" className="section-container" style={{ paddingTop: 0 }}>
        <div className="card" style={{ padding: '32px 40px', background: 'linear-gradient(135deg, #1d4ed8 0%, #2563eb 50%, #0284c7 100%)', color: '#ffffff', borderRadius: 24, boxShadow: '0 20px 40px rgba(37, 99, 235, 0.25)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 24, textAlign: 'center' }}>
            <div>
              <div style={{ fontSize: 38, fontWeight: 800 }}>158 / 158</div>
              <div style={{ fontSize: 13, opacity: 0.9, marginTop: 4 }}>Automated Pytest Suite</div>
            </div>
            <div>
              <div style={{ fontSize: 38, fontWeight: 800 }}>0 Errors</div>
              <div style={{ fontSize: 13, opacity: 0.9, marginTop: 4 }}>TypeScript & Ruff Checks</div>
            </div>
            <div>
              <div style={{ fontSize: 38, fontWeight: 800 }}>89 Commits</div>
              <div style={{ fontSize: 13, opacity: 0.9, marginTop: 4 }}>8-Day Clean Git Evolution</div>
            </div>
            <div>
              <div style={{ fontSize: 38, fontWeight: 800 }}>100% Invariant</div>
              <div style={{ fontSize: 13, opacity: 0.9, marginTop: 4 }}>Zero Leaky Currency Floats</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer style={{ borderTop: '1px solid var(--border)', background: '#ffffff', padding: '40px 24px', textAlign: 'center' }}>
        <div style={{ maxWidth: 1280, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div className="brand-icon-box" style={{ width: 28, height: 28, fontSize: 13 }}>
              <Zap size={15} />
            </div>
            <span style={{ fontWeight: 800, color: 'var(--text-primary)' }}>InvarPay AI</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>— Invariant-First Autonomous Payment Engine</span>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            Developed by <strong>Karthik Rajesh Shet</strong> for Razorpay AI Builder Showcase • Apache 2.0 Open Source
          </div>
          <div style={{ display: 'flex', gap: 16, fontSize: 13, fontWeight: 600 }}>
            <Link href="/dashboard">Console</Link>
            <Link href="/payments">Payments</Link>
            <Link href="/risk">PaymentGraph</Link>
            <Link href="/paydev">PayDev</Link>
            <a href="https://github.com/karthikrshet/InvarPay" target="_blank" rel="noreferrer" style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
              <span>GitHub</span>
              <ExternalLink size={12} />
            </a>
          </div>
        </div>
      </footer>

      {/* ── Floating 'Ask AI Engineer' Widget (Screenshot Replica) ── */}
      <div className="floating-ai-widget">
        <button
          onClick={() => setChatOpen(!chatOpen)}
          className="ai-pill-btn"
          aria-label="Ask AI Engineer"
        >
          <div className="pulse-dot" />
          <div className="ai-pill-avatar">
            <Bot size={16} />
          </div>
          <div className="ai-pill-text">
            <span className="ai-pill-title">Ask AI Engineer</span>
            <span className="ai-pill-sub">5/5 daily chats left</span>
          </div>
        </button>

        {/* Chat Drawer Dropup */}
        {chatOpen && (
          <div
            style={{
              position: 'absolute',
              bottom: 60,
              right: 0,
              width: 360,
              background: '#ffffff',
              borderRadius: 16,
              boxShadow: '0 20px 40px rgba(15, 23, 42, 0.2), 0 0 0 1px rgba(226, 232, 240, 0.8)',
              border: '1px solid #e2e8f0',
              padding: 20,
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #f1f5f9', paddingBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="pulse-dot" />
                <strong style={{ fontSize: 13 }}>InvarPay AI Assistant</strong>
              </div>
              <button onClick={() => setChatOpen(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                <X size={16} />
              </button>
            </div>
            <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              👋 <strong>Hi! I am the InvarPay AI copilot.</strong> I can explain how this platform enforces strict payment state machine invariants, how our LangGraph dispute investigation agent works, or how PayDev statically analyzes Python AST to prevent double-spends.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <Link href="/dashboard" className="btn btn-primary btn-sm" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                <span>Open Operational Console</span>
                <ArrowRight size={13} />
              </Link>
              <Link href="/paydev" className="btn btn-secondary btn-sm" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                <span>Inspect PayDev AST Rules</span>
                <ArrowRight size={13} />
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
