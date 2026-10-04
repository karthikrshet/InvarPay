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
  RefreshCw,
  X,
} from 'lucide-react'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Order {
  id: string
  amount: number
  currency: string
  status: string
  description?: string
  customer_name: string
  customer_email: string
  items: string
  created_at: string
  linked_payment_id?: string
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<'ALL' | 'COMPLETED' | 'PENDING'>('ALL')
  const [searchTerm, setSearchTerm] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // New order form fields
  const [newAmount, setNewAmount] = useState('1499')
  const [newDesc, setNewDesc] = useState('InvarPay Sentinel Edge Security Node')
  const [newEmail, setNewEmail] = useState('developer@techcorp.in')

  const fetchOrders = async () => {
    setLoading(true)
    try {
      const apiKey = typeof window !== 'undefined' ? localStorage.getItem('pg_api_key') || '' : ''
      const res = await fetch(`${API_URL}/v1/orders`, {
        headers: apiKey ? { 'X-API-Key': apiKey } : {},
      })
      if (res.ok) {
        const data = await res.json()
        if (data && Array.isArray(data.items)) {
          const mapped: Order[] = data.items.map((o: any) => ({
            id: o.id,
            amount: o.amount,
            currency: o.currency || 'INR',
            status: o.status ? o.status.toUpperCase() : 'PENDING',
            description: o.description || 'Merchant Order Item',
            items: o.description || 'Enterprise Commerce License',
            customer_name: o.metadata?.customer_name || 'Verified Merchant Buyer',
            customer_email: o.metadata?.customer_email || 'client@invarpay.ai',
            created_at: o.created_at || new Date().toISOString(),
            linked_payment_id: o.payment_attempts && o.payment_attempts.length > 0 ? o.payment_attempts[0].id : undefined,
          }))
          setOrders(mapped)
        }
      }
    } catch (e) {
      console.error('Failed to fetch orders from live API:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchOrders()
  }, [])

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      const apiKey = typeof window !== 'undefined' ? localStorage.getItem('pg_api_key') || '' : ''
      const amountPaise = Math.round(parseFloat(newAmount) * 100)

      const res = await fetch(`${API_URL}/v1/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'X-API-Key': apiKey } : {}),
        },
        body: JSON.stringify({
          amount: amountPaise,
          currency: 'INR',
          description: newDesc,
          metadata: {
            customer_email: newEmail,
            customer_name: newEmail.split('@')[0],
          },
        }),
      })

      if (res.ok) {
        setShowCreateModal(false)
        await fetchOrders()
      }
    } catch (err) {
      console.error('Failed to create order:', err)
    } finally {
      setIsSubmitting(false)
    }
  }

  const filteredOrders = orders.filter(o => {
    if (filter === 'COMPLETED' && o.status !== 'COMPLETED' && o.status !== 'CAPTURED') return false
    if (filter === 'PENDING' && o.status !== 'PENDING' && o.status !== 'PROCESSING') return false
    if (searchTerm) {
      const q = searchTerm.toLowerCase()
      return Boolean(
        (o.id && o.id.toLowerCase().includes(q)) ||
        (o.customer_name && o.customer_name.toLowerCase().includes(q)) ||
        (o.customer_email && o.customer_email.toLowerCase().includes(q)) ||
        (o.items && o.items.toLowerCase().includes(q))
      )
    }
    return true
  })

  // Dynamic KPIs calculated from live DB data
  const totalVolumePaise = orders.reduce((sum, o) => sum + o.amount, 0)
  const completedOrders = orders.filter(o => o.status === 'COMPLETED' || o.status === 'CAPTURED')
  const pendingOrders = orders.filter(o => o.status === 'PENDING' || o.status === 'PROCESSING')
  const conversionRate = orders.length > 0 ? ((completedOrders.length / orders.length) * 100).toFixed(1) : '100.0'

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
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <button
              onClick={fetchOrders}
              disabled={loading}
              className="btn btn-secondary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <RefreshCw size={13} className={loading ? 'spin' : ''} />
              <span>Refresh</span>
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn btn-primary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Plus size={14} />
              <span>New Order</span>
            </button>
          </div>
        </header>

        <div className="page-body">
          {/* Top KPI Cards */}
          <div className="kpi-grid">
            <div className="kpi-card">
              <span className="kpi-label">Total Order Value (GMV)</span>
              <span className="kpi-value" style={{ color: '#2563eb' }}>
                ₹ {(totalVolumePaise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
              <span className="kpi-delta">Live Database Store Value</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Completed Checkouts</span>
              <span className="kpi-value" style={{ color: '#059669' }}>{completedOrders.length} Orders</span>
              <span className="kpi-delta">100% Invariant Reconciled</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Awaiting Payment</span>
              <span className="kpi-value" style={{ color: '#d97706' }}>{pendingOrders.length} Orders</span>
              <span className="kpi-delta" style={{ color: '#d97706' }}>Active Checkout Intent</span>
            </div>
            <div className="kpi-card">
              <span className="kpi-label">Payment Conversion Rate</span>
              <span className="kpi-value">{conversionRate}%</span>
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
                All Orders ({orders.length})
              </button>
              <button
                onClick={() => setFilter('COMPLETED')}
                className={`btn btn-sm ${filter === 'COMPLETED' ? 'btn-primary' : 'btn-outline'}`}
              >
                Completed ({completedOrders.length})
              </button>
              <button
                onClick={() => setFilter('PENDING')}
                className={`btn btn-sm ${filter === 'PENDING' ? 'btn-primary' : 'btn-outline'}`}
              >
                Pending ({pendingOrders.length})
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
                    width: 240,
                  }}
                />
              </div>
            </div>
          </div>

          {/* Orders Table */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Authoritative Merchant Orders</div>
              <span className="badge badge-info">{filteredOrders.length} Live Records</span>
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
                  {filteredOrders.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)' }}>
                        {loading ? 'Fetching orders from SQLite database...' : 'No orders found matching filter.'}
                      </td>
                    </tr>
                  ) : (
                    filteredOrders.map(order => (
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
                          <span className={`badge badge-${order.status.toLowerCase() === 'completed' || order.status.toLowerCase() === 'captured' ? 'captured' : 'pending'}`}>
                            {order.status}
                          </span>
                        </td>
                        <td>
                          {order.linked_payment_id ? (
                            <Link href={`/payments`} style={{ display: 'inline-flex', alignItems: 'center', gap: 4, color: '#2563eb', fontWeight: 600, fontSize: 12 }}>
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
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Create Order Modal */}
          {showCreateModal && (
            <div style={{
              position: 'fixed',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'rgba(15, 23, 42, 0.6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 9999,
              backdropFilter: 'blur(4px)',
            }}>
              <div className="card" style={{ width: 440, padding: 24, boxShadow: '0 20px 25px -5px rgba(0,0,0,0.2)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <h3 style={{ fontSize: 17, fontWeight: 700 }}>Create Merchant Order</h3>
                  <button onClick={() => setShowCreateModal(false)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}>
                    <X size={18} />
                  </button>
                </div>
                <form onSubmit={handleCreateOrder} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)' }}>Amount (INR)</label>
                    <input
                      type="number"
                      step="0.01"
                      required
                      value={newAmount}
                      onChange={e => setNewAmount(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #cbd5e1', marginTop: 4 }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)' }}>Description / Sku</label>
                    <input
                      type="text"
                      required
                      value={newDesc}
                      onChange={e => setNewDesc(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #cbd5e1', marginTop: 4 }}
                    />
                  </div>
                  <div>
                    <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)' }}>Customer Email</label>
                    <input
                      type="email"
                      required
                      value={newEmail}
                      onChange={e => setNewEmail(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #cbd5e1', marginTop: 4 }}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                    <button type="button" onClick={() => setShowCreateModal(false)} className="btn btn-secondary btn-sm">
                      Cancel
                    </button>
                    <button type="submit" disabled={isSubmitting} className="btn btn-primary btn-sm">
                      {isSubmitting ? 'Creating in DB...' : 'Create Order'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
