'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Sidebar } from '../../components/Sidebar'
import {
  Package,
  Plus,
  Search,
  ExternalLink,
  CheckCircle2,
  Clock,
  ArrowRight,
  Filter,
  IndianRupee,
  ShoppingBag,
} from 'lucide-react'

interface Order {
  id: string
  amount: number
  currency: string
  status: string
  customer_name: string
  customer_email: string
  items: string
  created_at: string
  linked_payment_id?: string
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [filter, setFilter] = useState<'ALL' | 'COMPLETED' | 'PENDING'>('ALL')
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    setOrders([
      {
        id: 'ord_01J8K3R4P9M01',
        amount: 499900,
        currency: 'INR',
        status: 'COMPLETED',
        customer_name: 'Aditi Sharma',
        customer_email: 'aditi.sharma@techcorp.in',
        items: '2x InvarPay Hardware Enclave Key',
        created_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
        linked_payment_id: 'pay_01J8K3R4P9M01',
      },
      {
        id: 'ord_01J8K3Q8N2B02',
        amount: 85000,
        currency: 'INR',
        status: 'PROCESSING',
        customer_name: 'Rahul Verma',
        customer_email: 'r.verma@fintechlabs.co',
        items: '1x Developer API Security Token',
        created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
        linked_payment_id: 'pay_01J8K3Q8N2B02',
      },
      {
        id: 'ord_01J8K3M1K7C03',
        amount: 1250000,
        currency: 'INR',
        status: 'COMPLETED',
        customer_name: 'Vikram Mehta',
        customer_email: 'vikram@enterprise-saas.com',
        items: '1x Annual Enterprise Multi-Tenant License',
        created_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
        linked_payment_id: 'pay_01J8K3M1K7C03',
      },
      {
        id: 'ord_01J8K3F9J4D04',
        amount: 29900,
        currency: 'INR',
        status: 'PENDING',
        customer_name: 'Pooja Iyer',
        customer_email: 'pooja.i@growthai.io',
        items: '1x Fintech Engineering Handbook',
        created_at: new Date(Date.now() - 1000 * 60 * 240).toISOString(),
      },
      {
        id: 'ord_01J8K3A2H8E05',
        amount: 349900,
        currency: 'INR',
        status: 'COMPLETED',
        customer_name: 'Suresh Patel',
        customer_email: 'suresh@mumbai-retail.in',
        items: '5x Merchant Checkout Hardware Key',
        created_at: new Date(Date.now() - 1000 * 60 * 360).toISOString(),
        linked_payment_id: 'pay_01J8K3A2H8E05',
      },
    ])
  }, [])

  const filteredOrders = orders.filter(o => {
    if (filter === 'COMPLETED' && o.status !== 'COMPLETED') return false
    if (filter === 'PENDING' && o.status !== 'PENDING' && o.status !== 'PROCESSING') return false
    if (searchTerm) {
      const q = searchTerm.toLowerCase()
      return (
        Boolean(
          (o.id && o.id.toLowerCase().includes(q)) ||
          (o.customer_name && o.customer_name.toLowerCase().includes(q)) ||
          (o.customer_email && o.customer_email.toLowerCase().includes(q))
        )
      )
    }
    return true
  })

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 className="page-title">Orders & Checkouts</h1>
              <span className="badge badge-verified">
                <CheckCircle2 size={11} />
                <span>STATE MACHINE BOUND</span>
              </span>
            </div>
            <p className="page-subtitle">Track merchant orders, customer intent, and linked Razorpay test payment attempts</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>INTEGER MINOR UNITS ONLY</span>
          </div>
        </header>

        <div className="page-body">
          {/* Top KPI Cards */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Total Order Value (GMV)</span>
              <span className="kpi-value" style={{ color: '#2563eb' }}>₹ 22,14,700.00</span>
              <span className="kpi-delta">↑ 14.8% growth vs last week</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Completed Checkouts</span>
              <span className="kpi-value" style={{ color: '#059669' }}>4 Orders</span>
              <span className="kpi-delta">100% Invariant Reconciled</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Awaiting Payment</span>
              <span className="kpi-value" style={{ color: '#d97706' }}>1 Order</span>
              <span className="kpi-delta" style={{ color: '#d97706' }}>TTL expires in 22 mins</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Payment Conversion Rate</span>
              <span className="kpi-value">92.4%</span>
              <span className="kpi-delta">Zero double-capture errors</span>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="card" style={{ marginBottom: 24, padding: '14px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
                <Filter size={14} /> Filter:
              </span>
              <button
                onClick={() => setFilter('ALL')}
                className={`btn btn-sm ${filter === 'ALL' ? 'btn-primary' : 'btn-outline'}`}
              >
                All Orders
              </button>
              <button
                onClick={() => setFilter('COMPLETED')}
                className={`btn btn-sm ${filter === 'COMPLETED' ? 'btn-primary' : 'btn-outline'}`}
              >
                Completed
              </button>
              <button
                onClick={() => setFilter('PENDING')}
                className={`btn btn-sm ${filter === 'PENDING' ? 'btn-primary' : 'btn-outline'}`}
              >
                Pending
              </button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ position: 'relative' }}>
                <Search size={14} style={{ position: 'absolute', left: 10, top: 10, color: '#94a3b8' }} />
                <input
                  type="text"
                  placeholder="Search order or customer..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  style={{
                    padding: '7px 12px 7px 32px',
                    borderRadius: 20,
                    border: '1px solid #cbd5e1',
                    fontSize: 13,
                    outline: 'none',
                    width: 220,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Orders Table */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Authoritative Merchant Orders</div>
              <span className="badge badge-info">{filteredOrders.length} Records</span>
            </div>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Order ID</th>
                    <th>Customer</th>
                    <th>Items Summary</th>
                    <th>Gross Amount</th>
                    <th>Status</th>
                    <th>Linked Payment</th>
                    <th>Created At</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredOrders.map(order => (
                    <tr key={order.id}>
                      <td className="mono" style={{ fontWeight: 600, color: 'var(--brand-primary)' }}>
                        {order.id}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{order.customer_name}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{order.customer_email}</div>
                      </td>
                      <td style={{ fontSize: 12.5 }}>{order.items}</td>
                      <td style={{ fontWeight: 700 }}>
                        {order.currency} {(order.amount / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </td>
                      <td>
                        <span className={`badge badge-${order.status.toLowerCase()}`}>
                          {order.status}
                        </span>
                      </td>
                      <td>
                        {order.linked_payment_id ? (
                          <Link href={`/payments/${order.linked_payment_id}`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: '#2563eb', fontWeight: 600, fontSize: 12 }}>
                            <span>{order.linked_payment_id.slice(0, 15)}...</span>
                            <ExternalLink size={11} />
                          </Link>
                        ) : (
                          <span style={{ fontSize: 11, color: '#d97706' }}>Awaiting Payment</span>
                        )}
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {new Date(order.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                      </td>
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
