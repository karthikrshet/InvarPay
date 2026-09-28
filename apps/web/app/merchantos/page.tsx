'use client'

import { useState } from 'react'
import { Sidebar } from '../../components/Sidebar'
import {
  TrendingUp,
  Receipt,
  CheckCircle2,
  AlertCircle,
  FileSpreadsheet,
  Calendar,
  IndianRupee,
  ArrowRight,
  Filter,
  Plus,
} from 'lucide-react'

interface Invoice {
  id: string
  customer: string
  amount: number
  currency: string
  status: 'PAID' | 'PENDING' | 'OVERDUE'
  due_date: string
  payment_link_id?: string
}

export default function MerchantOSPage() {
  const [activeTab, setActiveTab] = useState<'SETTLEMENTS' | 'INVOICES' | 'PROJECTIONS'>('SETTLEMENTS')

  const invoices: Invoice[] = [
    {
      id: 'inv_01J8K9901',
      customer: 'Acme SaaS India Pvt Ltd',
      amount: 2500000,
      currency: 'INR',
      status: 'PAID',
      due_date: '2026-10-01',
      payment_link_id: 'plink_01J8K3R4P9M01',
    },
    {
      id: 'inv_01J8K9902',
      customer: 'Starlight Retailers Bangalore',
      amount: 780000,
      currency: 'INR',
      status: 'PENDING',
      due_date: '2026-10-05',
      payment_link_id: 'plink_01J8K3Q8N2B02',
    },
    {
      id: 'inv_01J8K9903',
      customer: 'Apex Logistics Mumbai',
      amount: 1420000,
      currency: 'INR',
      status: 'PAID',
      due_date: '2026-09-25',
      payment_link_id: 'plink_01J8K3M1K7C03',
    },
    {
      id: 'inv_01J8K9904',
      customer: 'Zenith Cloud Infrastructure',
      amount: 4950000,
      currency: 'INR',
      status: 'PENDING',
      due_date: '2026-10-12',
    },
  ]

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 className="page-title">MerchantOS AI — Financial Treasury</h1>
              <span className="badge badge-verified">
                <CheckCircle2 size={11} />
                <span>DUAL-ENTRY BALANCED</span>
              </span>
            </div>
            <p className="page-subtitle">Settlement CSV parsing, automated bank UTR reconciliation, invoice tracking & cashflow forecasting</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>INTEGER MINOR UNITS ONLY</span>
          </div>
        </header>

        <div className="page-body">
          {/* Top Cashflow Projections */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Projected 30d Inflow</span>
              <span className="kpi-value" style={{ color: '#059669' }}>₹ 47,20,000.00</span>
              <span className="kpi-delta">± ₹ 35,000 bound (95% confidence)</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">60d Runway Forecast</span>
              <span className="kpi-value" style={{ color: '#2563eb' }}>₹ 92,50,000.00</span>
              <span className="kpi-delta">Based on 14-day rolling mean velocity</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Total Settled (MTD)</span>
              <span className="kpi-value">₹ 1,18,45,000.00</span>
              <span className="kpi-delta">100% matched to bank UTR credits</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Reconciliation Variance</span>
              <span className="kpi-value" style={{ color: '#059669' }}>₹ 0.00</span>
              <span className="kpi-delta">Zero unexplained ledger drift</span>
            </div>
          </div>

          {/* Tab Selector */}
          <div className="card" style={{ marginBottom: 24, padding: '12px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setActiveTab('SETTLEMENTS')}
                className={`btn btn-sm ${activeTab === 'SETTLEMENTS' ? 'btn-primary' : 'btn-outline'}`}
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <FileSpreadsheet size={14} />
                <span>Bank Settlement Reconciler</span>
              </button>
              <button
                onClick={() => setActiveTab('INVOICES')}
                className={`btn btn-sm ${activeTab === 'INVOICES' ? 'btn-primary' : 'btn-outline'}`}
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Receipt size={14} />
                <span>Invoice Tracker</span>
              </button>
              <button
                onClick={() => setActiveTab('PROJECTIONS')}
                className={`btn btn-sm ${activeTab === 'PROJECTIONS' ? 'btn-primary' : 'btn-outline'}`}
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <TrendingUp size={14} />
                <span>Cashflow Projections</span>
              </button>
            </div>

            <span className="badge badge-info">
              Razorpay Settlement Cycle: T+1 Morning
            </span>
          </div>

          {/* Tab 1: Bank Settlement Reconciler */}
          {activeTab === 'SETTLEMENTS' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div className="card">
                <div className="card-header">
                  <div>
                    <div className="card-title">Settlement Batch: set_20260928_hdfc_991</div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>Bank UTR Reference: UTIB0001928374 • Settled to HDFC Current Account (•••4012)</div>
                  </div>
                  <span className="badge badge-success">RECONCILED & BALANCED</span>
                </div>

                <div className="card-body">
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, marginBottom: 20 }}>
                    <div style={{ background: '#f8fafc', padding: 14, borderRadius: 8, border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>GROSS TRANSACTION AMOUNT</div>
                      <div style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)' }}>₹ 15,00,000.00</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>150,000,000 paise</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: 14, borderRadius: 8, border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>GATEWAY FEE (2.0%)</div>
                      <div style={{ fontSize: 18, fontWeight: 800, color: '#d97706' }}>- ₹ 30,000.00</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Standard Razorpay MDR</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: 14, borderRadius: 8, border: '1px solid #e2e8f0' }}>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600 }}>INPUT GST (18%)</div>
                      <div style={{ fontSize: 18, fontWeight: 800, color: '#2563eb' }}>- ₹ 5,400.00</div>
                      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Eligible for ITC credit</div>
                    </div>
                    <div style={{ background: '#ecfdf5', padding: 14, borderRadius: 8, border: '1px solid #a7f3d0' }}>
                      <div style={{ fontSize: 11, color: '#065f46', fontWeight: 600 }}>NET BANK CREDIT (UTR)</div>
                      <div style={{ fontSize: 18, fontWeight: 800, color: '#059669' }}>₹ 14,64,600.00</div>
                      <div style={{ fontSize: 11, color: '#059669' }}>100% Verified Match</div>
                    </div>
                  </div>

                  {/* Dual-Entry Ledger Entry Box */}
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
                      Double-Entry General Ledger Journal Entry
                    </div>
                    <div className="code-box" style={{ fontSize: 12.5, lineHeight: 1.7 }}>
                      <div style={{ color: '#4ade80' }}>Dr. 1010 Bank Checking Account (HDFC)        : ₹ 14,64,600.00</div>
                      <div style={{ color: '#60a5fa' }}>Dr. 5020 Payment Gateway Processing Fees       : ₹    30,000.00</div>
                      <div style={{ color: '#60a5fa' }}>Dr. 1080 Input GST Tax Credit Receivable       : ₹     5,400.00</div>
                      <div style={{ color: '#f87171' }}>Cr. 1200 Merchant Accounts Receivable          : ₹ 15,00,000.00</div>
                      <div style={{ borderTop: '1px solid #334155', marginTop: 8, paddingTop: 6, color: '#38bdf8' }}>
                        LEDGER EQUALITY CHECK: SUM(Debits) == SUM(Credits) [DIFFERENCE: ₹ 0.00]
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Invoices */}
          {activeTab === 'INVOICES' && (
            <div className="card">
              <div className="card-header">
                <div className="card-title">Commercial B2B Invoices</div>
                <button className="btn btn-primary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Plus size={13} />
                  <span>Create Invoice</span>
                </button>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Invoice ID</th>
                      <th>Customer Name</th>
                      <th>Gross Amount</th>
                      <th>Status</th>
                      <th>Due Date</th>
                      <th>Payment Link</th>
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map(inv => (
                      <tr key={inv.id}>
                        <td className="mono" style={{ fontWeight: 600, color: 'var(--brand-primary)' }}>{inv.id}</td>
                        <td style={{ fontWeight: 600 }}>{inv.customer}</td>
                        <td style={{ fontWeight: 700 }}>
                          {inv.currency} {(inv.amount / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                        <td>
                          <span className={`badge badge-${inv.status === 'PAID' ? 'captured' : 'pending'}`}>
                            {inv.status}
                          </span>
                        </td>
                        <td style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{inv.due_date}</td>
                        <td>
                          {inv.payment_link_id ? (
                            <span className="mono" style={{ fontSize: 11, color: '#2563eb' }}>
                              {inv.payment_link_id}
                            </span>
                          ) : (
                            <button className="btn btn-outline btn-sm" style={{ padding: '2px 8px', fontSize: 11 }}>
                              Generate Link
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Tab 3: Projections */}
          {activeTab === 'PROJECTIONS' && (
            <div className="card" style={{ padding: 24 }}>
              <div className="card-title" style={{ marginBottom: 12 }}>3-Month Rolling Cashflow Trajectory Model</div>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 20 }}>
                Autonomous Monte Carlo projections based on 90-day recurring subscription cohorts, churn rates, and historical payment gateway capture latencies.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                <div style={{ background: '#f8fafc', padding: 18, borderRadius: 10, border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)' }}>OCTOBER 2026 (PROJECTED)</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: '#059669', margin: '6px 0' }}>₹ 51,80,000</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>Confidence Interval: [₹ 48.5L - ₹ 54.2L]</div>
                </div>
                <div style={{ background: '#f8fafc', padding: 18, borderRadius: 10, border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)' }}>NOVEMBER 2026 (PROJECTED)</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: '#2563eb', margin: '6px 0' }}>₹ 58,40,000</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>Confidence Interval: [₹ 53.0L - ₹ 62.1L]</div>
                </div>
                <div style={{ background: '#f8fafc', padding: 18, borderRadius: 10, border: '1px solid #e2e8f0' }}>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-muted)' }}>DECEMBER 2026 (PROJECTED)</div>
                  <div style={{ fontSize: 24, fontWeight: 800, color: '#4f46e5', margin: '6px 0' }}>₹ 67,20,000</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>Confidence Interval: [₹ 60.5L - ₹ 73.8L]</div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
