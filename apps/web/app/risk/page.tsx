'use client'

import { useEffect, useState } from 'react'
import { Sidebar } from '../../components/Sidebar'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function RiskPage() {
  const [modelCard, setModelCard] = useState<any>(null)
  const [rules, setRules] = useState<any[]>([])
  const [benchmark, setBenchmark] = useState<any>(null)

  useEffect(() => {
    fetch(`${API_URL}/v1/risk/model-card`)
      .then(res => res.json())
      .then(data => setModelCard(data))
      .catch(() => {})

    fetch(`${API_URL}/v1/risk/rules`)
      .then(res => res.json())
      .then(data => setRules(data))
      .catch(() => {})

    fetch(`${API_URL}/v1/risk/benchmark`)
      .then(res => res.json())
      .then(data => setBenchmark(data))
      .catch(() => {})
  }, [])

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">PaymentGraph AI — Fraud Intelligence</h1>
            <p className="page-subtitle">Explainable risk scoring, deterministic signal rules & transparent model cards</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>SYNTHETIC BENCHMARK</span>
          </div>
        </header>

        {/* Model Transparency & Disclaimer Notice */}
        <div className="card" style={{ borderLeft: '4px solid #3b82f6', marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>
            🛡️ Research Prototype & Transparency Notice
          </h3>
          <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6, fontSize: 14 }}>
            PaymentGraph generates explainable risk signals based on deterministic heuristics and synthetic benchmark calibration.
            <strong> Never assert an authoritative fraud score without verifiable evidence.</strong> Automated charge denial is prohibited without qualified human review.
          </p>
        </div>

        {/* Benchmark KPIs */}
        {benchmark && (
          <div className="kpi-grid" style={{ marginBottom: 24 }}>
            <div className="kpi-card">
              <span className="kpi-label">Precision</span>
              <span className="kpi-value" style={{ color: '#10b981' }}>{(benchmark.metrics.precision * 100).toFixed(1)}%</span>
              <span className="kpi-delta">Synthetic Dataset v1</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Recall</span>
              <span className="kpi-value" style={{ color: '#3b82f6' }}>{(benchmark.metrics.recall * 100).toFixed(1)}%</span>
              <span className="kpi-delta">50,000 synthetic records</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">PR-AUC</span>
              <span className="kpi-value" style={{ color: '#8b5cf6' }}>{(benchmark.metrics.pr_auc * 100).toFixed(1)}%</span>
              <span className="kpi-delta">Calibrated threshold 0.65</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">False Positive Rate</span>
              <span className="kpi-value" style={{ color: '#f59e0b' }}>{(benchmark.metrics.false_positive_rate * 100).toFixed(1)}%</span>
              <span className="kpi-delta">Fixed alert volume</span>
            </div>
          </div>
        )}

        {/* Deterministic Rules */}
        <div className="card" style={{ marginBottom: 24 }}>
          <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>
            Deterministic Risk Signals & Weights
          </h2>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Rule ID</th>
                  <th>Signal Name</th>
                  <th>Category</th>
                  <th>Weight</th>
                  <th>Confidence</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {rules.map(rule => (
                  <tr key={rule.id}>
                    <td><code>{rule.id}</code></td>
                    <td style={{ fontWeight: 600 }}>{rule.name}</td>
                    <td>{rule.category}</td>
                    <td><span className="badge badge-pending">{rule.weight}x</span></td>
                    <td>
                      <span className={`badge badge-${rule.confidence === 'high' ? 'captured' : 'unknown'}`}>
                        {rule.confidence.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ color: 'var(--color-text-secondary)', fontSize: 13 }}>
                      {rule.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Model Card */}
        {modelCard && (
          <div className="card">
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>
              Model Card Specifications
            </h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
              <div>
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>MODEL NAME</span>
                <p style={{ fontWeight: 600, marginTop: 4 }}>{modelCard.model_name}</p>
              </div>
              <div>
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>DATA PROVENANCE</span>
                <p style={{ fontWeight: 600, marginTop: 4 }}>{modelCard.data_provenance}</p>
              </div>
              <div>
                <span style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>INTENDED USE</span>
                <p style={{ fontWeight: 600, marginTop: 4 }}>{modelCard.intended_use}</p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
