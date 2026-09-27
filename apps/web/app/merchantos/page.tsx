'use client'

import { useEffect, useState } from 'react'
import { Sidebar } from '../../components/Sidebar'

export default function MerchantOSPage() {
  const [invoices, setInvoices] = useState<any[]>([])

  useEffect(() => {
    setInvoices([
      {
        id: 'inv_01HZX3301',
        customer: 'Acme SaaS Corp',
        amount: 2500000,
        currency: 'INR',
        status: 'PAID',
        due_date: '2026-10-01',
      },
      {
        id: 'inv_01HZX3302',
        customer: 'Starlight Retailers',
        amount: 780000,
        currency: 'INR',
        status: 'PENDING',
        due_date: '2026-10-05',
      },
      {
        id: 'inv_01HZX3303',
        customer: 'Apex Logistics',
        amount: 1420000,
        currency: 'INR',
        status: 'OVERDUE',
        due_date: '2026-09-20',
      },
    ])
  }, [])

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">MerchantOS AI — Financial Assistant</h1>
            <p className="page-subtitle">Settlement reconciliation, invoice tracking & cash-flow projections</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>INTEGER MINOR UNITS ONLY</span>
          </div>
        </header>

        {/* Cashflow Projections with Explicit Assumptions */}
        <div className="kpi-grid" style={{ marginBottom: 24 }}>
          <div className="kpi-card">
            <span className="kpi-label">Projected 30d Inflow</span>
            <span className="kpi-value" style={{ color: '#10b981' }}>₹ 47,000.00</span>
            <span className="kpi-delta">± ₹ 3,500 bound (95% confidence)</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Pending Settlements</span>
            <span className="kpi-value" style={{ color: '#3b82f6' }}>₹ 12,500.00</span>
            <span className="kpi-delta">T+2 settlement cycle</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Unreconciled Difference</span>
            <span className="kpi-value" style={{ color: '#10b981' }}>₹ 0.00</span>
            <span className="kpi-delta">100% matched to date</span>
          </div>
          <div className="kpi-card">
            <span className="kpi-label">Overdue Invoices</span>
            <span className="kpi-value" style={{ color: '#ef4444' }}>₹ 14,200.00</span>
            <span className="kpi-delta">1 invoice requiring reminder</span>
          </div>
        </div>

        {/* Projection Assumptions Callout */}
        <div className="card" style={{ borderLeft: '4px solid #10b981', marginBottom: 24 }}>
          <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>
            📊 Financial Projection Assumptions & Error Bounds
          </h3>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 13, lineHeight: 1.5 }}>
            Forecast assumes historical 87% on-time payment conversion, zero gateway downtime, and standard T+2 settlement windows.
            No automated collections without merchant-approved reminder workflows.
          </p>
        </div>

        {/* Invoices Table */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 600 }}>Active Invoices</h2>
            <button className="btn btn-primary" style={{ padding: '6px 14px', fontSize: 13 }}>
              + Create Invoice
            </button>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Invoice ID</th>
                  <th>Customer</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Due Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map(inv => (
                  <tr key={inv.id}>
                    <td><code>{inv.id}</code></td>
                    <td style={{ fontWeight: 600 }}>{inv.customer}</td>
                    <td>{inv.currency} {(inv.amount / 100).toFixed(2)}</td>
                    <td>
                      <span className={`badge badge-${inv.status === 'PAID' ? 'captured' : (inv.status === 'OVERDUE' ? 'failed' : 'pending')}`}>
                        {inv.status}
                      </span>
                    </td>
                    <td>{inv.due_date}</td>
                    <td>
                      {inv.status === 'OVERDUE' ? (
                        <button className="btn" style={{ padding: '4px 10px', fontSize: 12 }}>
                          Request Reminder Approval
                        </button>
                      ) : (
                        <span style={{ color: 'var(--color-text-muted)', fontSize: 12 }}>None</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  )
}
