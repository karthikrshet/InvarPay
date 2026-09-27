'use client'

import { useEffect, useState } from 'react'
import { Sidebar } from '../../components/Sidebar'

export default function ShopPage() {
  const [catalog, setCatalog] = useState<any[]>([])
  const [cart, setCart] = useState<{ id: string; name: string; price: number; qty: number }[]>([])
  const [confirmed, setConfirmed] = useState(false)
  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null)

  useEffect(() => {
    setCatalog([
      { id: 'prod_001', name: 'Developer Security Token', price: 299900, stock: 15, currency: 'INR' },
      { id: 'prod_002', name: 'Fintech Engineering Handbook', price: 99900, stock: 42, currency: 'INR' },
      { id: 'prod_003', name: 'InvarPay AI Hardware Enclave Key', price: 799900, stock: 8, currency: 'INR' },
    ])
  }, [])

  const addToCart = (prod: any) => {
    setCart(prev => {
      const existing = prev.find(item => item.id === prod.id)
      if (existing) {
        return prev.map(item => item.id === prod.id ? { ...item, qty: item.qty + 1 } : item)
      }
      return [...prev, { id: prod.id, name: prod.name, price: prod.price, qty: 1 }]
    })
    setConfirmed(false)
    setCheckoutUrl(null)
  }

  const totalAmount = cart.reduce((sum, item) => sum + item.price * item.qty, 0)

  const handleCheckout = () => {
    if (!confirmed) {
      alert('Buyer confirmation required! You must explicitly check the confirmation box.')
      return
    }
    // Simulate generating provider-hosted checkout URL
    setCheckoutUrl(`https://api.razorpay.com/v1/checkout/test_session_demo_${Date.now()}`)
  }

  return (
    <div className="layout">
      <Sidebar />
      <main className="main-content">
        <header className="page-header">
          <div>
            <h1 className="page-title">ShopAgent MCP — Agentic Commerce</h1>
            <p className="page-subtitle">Product discovery, inventory verification & buyer-confirmed checkout</p>
          </div>
          <div className="provider-pill">
            <span className="provider-dot" />
            <span>NO AUTONOMOUS CHARGES</span>
          </div>
        </header>

        {/* Safety Boundary Banner */}
        <div className="card" style={{ borderLeft: '4px solid #ef4444', marginBottom: 24 }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8, color: '#f87171' }}>
            🔒 Strict Customer Approval Gate (PCI-DSS Boundary)
          </h3>
          <p style={{ color: 'var(--color-text-secondary)', lineHeight: 1.6, fontSize: 14 }}>
            ShopAgent assists users in finding goods and managing carts, but <strong>CANNOT store payment card credentials or initiate autonomous financial transactions.</strong> Every purchase requires explicit human consent and redirects to the merchant's authorized provider checkout.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
          {/* Catalog */}
          <div className="card">
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Authorized Product Catalog</h2>
            <div style={{ display: 'grid', gap: 12 }}>
              {catalog.map(prod => (
                <div key={prod.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'rgba(255,255,255,0.03)', borderRadius: 8, border: '1px solid var(--color-border)' }}>
                  <div>
                    <span style={{ fontWeight: 600 }}>{prod.name}</span>
                    <div style={{ fontSize: 12, color: 'var(--color-text-muted)', marginTop: 4 }}>
                      Stock: {prod.stock} units · Real-time verified
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <span style={{ fontWeight: 600 }}>₹ {(prod.price / 100).toFixed(2)}</span>
                    <button
                      onClick={() => addToCart(prod)}
                      className="btn btn-primary"
                      style={{ padding: '6px 14px', fontSize: 13 }}
                    >
                      Add to Cart
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Cart & Buyer Gate */}
          <div className="card">
            <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Your Cart</h2>
            {cart.length === 0 ? (
              <p style={{ color: 'var(--color-text-muted)', fontSize: 14 }}>Cart is empty</p>
            ) : (
              <div>
                <div style={{ display: 'grid', gap: 8, marginBottom: 16 }}>
                  {cart.map(item => (
                    <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 14 }}>
                      <span>{item.name} × {item.qty}</span>
                      <span>₹ {((item.price * item.qty) / 100).toFixed(2)}</span>
                    </div>
                  ))}
                </div>

                <div style={{ paddingTop: 12, borderTop: '1px solid var(--color-border)', display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: 16, marginBottom: 16 }}>
                  <span>Total</span>
                  <span>₹ {(totalAmount / 100).toFixed(2)}</span>
                </div>

                {/* Explicit Buyer Confirmation Gate */}
                <div style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: 12, borderRadius: 6, marginBottom: 16 }}>
                  <label style={{ display: 'flex', gap: 8, cursor: 'pointer', fontSize: 13, color: '#fca5a5' }}>
                    <input
                      type="checkbox"
                      checked={confirmed}
                      onChange={e => setConfirmed(e.target.checked)}
                      style={{ marginTop: 2 }}
                    />
                    <span>I explicitly confirm and authorize this purchase order of ₹ {(totalAmount / 100).toFixed(2)}.</span>
                  </label>
                </div>

                <button
                  onClick={handleCheckout}
                  disabled={!confirmed}
                  className="btn btn-primary"
                  style={{ width: '100%', padding: '10px 0', opacity: confirmed ? 1 : 0.5 }}
                >
                  Proceed to Provider-Hosted Checkout
                </button>

                {checkoutUrl && (
                  <div style={{ marginTop: 16, padding: 12, background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: 6 }}>
                    <p style={{ fontSize: 12, color: '#6ee7b7', marginBottom: 6 }}>✓ Provider Checkout Session Ready:</p>
                    <code style={{ fontSize: 11, wordBreak: 'break-all' }}>{checkoutUrl}</code>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
