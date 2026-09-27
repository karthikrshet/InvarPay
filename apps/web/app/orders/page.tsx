'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Sidebar } from '../../components/Sidebar'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Order {
  id: string
  amount: number
  currency: string
  status: string
  customer_id?: string
  created_at: string
}

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Synthetic sample orders for demo
    setOrders([
      {
        id: 'ord_01HZX87654ABCD1234567890',
        amount: 499900,
        currency: 'INR',
        status: 'completed',
        customer_id: 'cust_01HZX1',
        created_at: new Date().toISOString(),
      },
      {
        id: 'ord_01HZX87654ABCD1234567891',
        amount: 125000,
        currency: 'INR',
        status: 'pending',
        customer_id: 'cust_01HZX2',
        created_at: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: 'ord_01HZX87654ABCD1234567892',
        amount: 89000,
        currency: 'INR',
        status: 'processing',
        customer_id: 'cust_01HZX3',
        created_at: new Date(Date.now() - 7200000).toISOString(),
      },
    ])
    setLoading(false)
  }, [])

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">Orders</h1>
            <p className="page-subtitle">Track merchant orders and linked payment attempts</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>AUTHORITATIVE STATE</span>
          </div>
        </header>

        <div className="card">
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Amount (Paise)</th>
                  <th>Formatted</th>
                  <th>Status</th>
                  <th>Customer</th>
                  <th>Created At</th>
                </tr>
              </thead>
              <tbody>
                {orders.map(order => (
                  <tr key={order.id}>
                    <td>
                      <code style={{ color: 'var(--color-primary)' }}>{order.id.slice(0, 16)}...</code>
                    </td>
                    <td>{order.amount.toLocaleString()}</td>
                    <td style={{ fontWeight: 600 }}>{order.currency} {(order.amount / 100).toFixed(2)}</td>
                    <td>
                      <span className={`badge badge-${order.status === 'completed' ? 'captured' : 'pending'}`}>
                        {order.status}
                      </span>
                    </td>
                    <td>{order.customer_id || 'Guest'}</td>
                    <td style={{ color: 'var(--color-text-muted)' }}>
                      {new Date(order.created_at).toLocaleTimeString()}
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
