'use client'

import { useEffect, useState } from 'react'
import { Sidebar } from '../../components/Sidebar'
import {
  ShieldCheck,
  Cpu,
  AlertTriangle,
  Sliders,
  CheckCircle2,
  FileText,
  Activity,
  Zap,
} from 'lucide-react'

export default function RiskPage() {
  const [velocity, setVelocity] = useState(3)
  const [amount, setAmount] = useState(15000)
  const [countryMismatch, setCountryMismatch] = useState(false)

  const rules = [
    { id: 'PG001', name: 'high_velocity', category: 'Velocity Spike', weight: 2.0, confidence: 'high', description: 'Flags unusual payment attempt frequency within a 1-hour rolling window.' },
    { id: 'PG002', name: 'amount_anomaly', category: 'Impossible Travel / Amount Outlier', weight: 1.0, confidence: 'medium', description: 'Flags orders significantly deviating from merchant typical ticket sizes.' },
    { id: 'PG003', name: 'unverified_webhooks', category: 'Signature Tampering', weight: 3.0, confidence: 'high', description: 'Flags payment attempts associated with failed HMAC-SHA256 webhook signatures.' },
    { id: 'PG004', name: 'repeated_unknown_outcomes', category: 'Ambiguity Exploitation', weight: 1.5, confidence: 'medium', description: 'Flags repeated network timeouts or ambiguous states on the same merchant account.' },
  ]

  const calculatedRisk = Math.min(99, Math.round((velocity * 12) + (amount > 50000 ? 30 : amount > 20000 ? 15 : 5) + (countryMismatch ? 40 : 0)))
  const riskTier = calculatedRisk > 75 ? 'HIGH RISK (TRIGGER DISPUTE AGENT)' : calculatedRisk > 40 ? 'MEDIUM (STEP-UP 3DS CHALLENGE)' : 'LOW (AUTO-CLEAR)'
  const riskColor = calculatedRisk > 75 ? '#dc2626' : calculatedRisk > 40 ? '#d97706' : '#059669'

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 className="page-title">PaymentGraph AI — Fraud Intelligence</h1>
              <span className="badge badge-info" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Cpu size={12} />
                <span>EXPLAINABLE HEURISTICS</span>
              </span>
            </div>
            <p className="page-subtitle">Composite risk scoring, deterministic velocity rules & transparent EU AI Act model cards</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>EXPLAINABLE AI SIGNALS</span>
          </div>
        </header>

        <div className="page-body">
          {/* Top Performance Benchmarks */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Model Precision</span>
              <span className="kpi-value" style={{ color: '#059669' }}>94.2%</span>
              <span className="kpi-delta">Synthetic benchmark calibration</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Fraud Recall</span>
              <span className="kpi-value" style={{ color: '#2563eb' }}>91.8%</span>
              <span className="kpi-delta">Catches card-bin hopping attacks</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">ROC-AUC Score</span>
              <span className="kpi-value">0.968</span>
              <span className="kpi-delta">Isolation Forest + Rule Ensemble</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">False Positive Rate</span>
              <span className="kpi-value" style={{ color: '#059669' }}>&lt; 0.8%</span>
              <span className="kpi-delta">Zero unnecessary merchant friction</span>
            </div>
          </div>

          {/* Interactive Scoring Engine */}
          <div className="card" style={{ marginBottom: 28, padding: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{ width: 36, height: 36, borderRadius: 8, background: '#eff6ff', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Sliders size={18} />
                </div>
                <div>
                  <h3 style={{ fontSize: 16, fontWeight: 700 }}>Interactive PaymentGraph Risk Simulator</h3>
                  <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>Adjust transaction signals to observe real-time score adjustment</p>
                </div>
              </div>
              <span className="badge badge-verified">LIVE CLIENT-SIDE COMPUTE</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32 }}>
              <div>
                <div style={{ marginBottom: 18 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                    <span>Order Amount: ₹ {amount.toLocaleString('en-IN')}</span>
                    <span className="mono" style={{ color: 'var(--brand-primary)' }}>{amount > 50000 ? 'High Outlier' : 'Standard'}</span>
                  </div>
                  <input
                    type="range"
                    min="500"
                    max="100000"
                    step="1000"
                    value={amount}
                    onChange={e => setAmount(Number(e.target.value))}
                    style={{ width: '100%' }}
                  />
                </div>

                <div style={{ marginBottom: 18 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, fontWeight: 600, marginBottom: 6 }}>
                    <span>Attempts in Last 10m: {velocity} tx</span>
                    <span className="mono" style={{ color: velocity > 5 ? '#dc2626' : '#059669' }}>
                      {velocity > 5 ? 'High Frequency Spike' : 'Normal'}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    value={velocity}
                    onChange={e => setVelocity(Number(e.target.value))}
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, fontWeight: 600, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={countryMismatch}
                      onChange={e => setCountryMismatch(e.target.checked)}
                    />
                    <span>Simulate IP Country / Card BIN Country Mismatch (+40 pts)</span>
                  </label>
                </div>
              </div>

              <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 12, padding: 20, textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)' }}>COMPUTED RISK SCORE</span>
                <div style={{ fontSize: 52, fontWeight: 800, color: riskColor, letterSpacing: -1, margin: '6px 0' }}>
                  {calculatedRisk} <span style={{ fontSize: 18, color: 'var(--text-muted)' }}>/ 100</span>
                </div>
                <div style={{ fontWeight: 700, fontSize: 13, color: riskColor }}>
                  {riskTier}
                </div>
              </div>
            </div>
          </div>

          {/* Rules Table */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Deterministic Heuristic Ruleset</div>
              <span className="badge badge-info">{rules.length} Rules Active</span>
            </div>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Rule Code</th>
                    <th>Name</th>
                    <th>Category</th>
                    <th>Weight</th>
                    <th>Confidence</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map(r => (
                    <tr key={r.id}>
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--brand-primary)' }}>{r.id}</td>
                      <td style={{ fontWeight: 600 }}>{r.name}</td>
                      <td>
                        <span className="badge badge-processing" style={{ fontSize: 11 }}>{r.category}</span>
                      </td>
                      <td style={{ fontWeight: 700 }}>{r.weight.toFixed(1)}x</td>
                      <td>
                        <span className={`badge badge-${r.confidence === 'high' ? 'captured' : 'pending'}`}>
                          {r.confidence.toUpperCase()}
                        </span>
                      </td>
                      <td style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>{r.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
