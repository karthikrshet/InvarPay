'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  CreditCard,
  Package,
  Search,
  Lock,
  ShieldCheck,
  Zap,
  TrendingUp,
  ShoppingCart,
  Settings,
  Sparkles,
  ChevronRight,
} from 'lucide-react'

export function Sidebar() {
  const pathname = usePathname()

  const coreNav = [
    { href: '/dashboard', icon: LayoutDashboard, label: 'Console Overview' },
    { href: '/payments', icon: CreditCard, label: 'Payment Attempts' },
    { href: '/orders', icon: Package, label: 'Orders & Checkouts' },
    { href: '/investigations', icon: Search, label: 'LangGraph Agent' },
    { href: '/audit', icon: Lock, label: 'Audit Log Chain' },
  ]

  const moduleNav = [
    { href: '/risk', icon: ShieldCheck, label: 'PaymentGraph AI', tag: 'ML' },
    { href: '/paydev', icon: Zap, label: 'PayDev AST Linter', tag: 'AST' },
    { href: '/merchantos', icon: TrendingUp, label: 'MerchantOS Ledger', tag: 'FIN' },
    { href: '/shop', icon: ShoppingCart, label: 'ShopAgent MCP', tag: 'MCP' },
  ]

  const adminNav = [
    { href: '/settings', icon: Settings, label: 'Settings & Adapters' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <Link href="/" className="logo-mark" style={{ textDecoration: 'none' }}>
          <div className="logo-icon">
            <Zap size={18} strokeWidth={2.5} />
          </div>
          <div>
            <div className="logo-text">InvarPay AI</div>
            <div style={{ fontSize: 10, color: 'var(--brand-primary)', fontWeight: 700, letterSpacing: '0.04em' }}>
              FINTECH ENGINE
            </div>
          </div>
        </Link>
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center' }}>
          <span
            className="logo-badge"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              background: '#ecfdf5',
              color: '#059669',
              borderColor: '#a7f3d0',
              fontSize: 10.5,
              fontWeight: 700,
              padding: '2.5px 8px',
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: '#10b981',
                boxShadow: '0 0 0 2px rgba(16, 185, 129, 0.25)',
              }}
            />
            DEMO MODE
          </span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <Link
          href="/"
          className="nav-item"
          style={{
            background: 'var(--brand-light)',
            color: 'var(--brand-primary)',
            fontWeight: 700,
            marginBottom: 8,
            border: '1px solid var(--brand-border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={16} />
            <span>Showcase Page</span>
          </div>
          <ChevronRight size={14} />
        </Link>

        <div className="nav-section-label">Core Operations</div>
        {coreNav.map(item => {
          const Icon = item.icon
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={16} strokeWidth={isActive ? 2.5 : 2} />
              <span>{item.label}</span>
            </Link>
          )
        })}

        <div className="nav-section-label" style={{ marginTop: 14 }}>Autonomous AI Engines</div>
        {moduleNav.map(item => {
          const Icon = item.icon
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={16} strokeWidth={isActive ? 2.5 : 2} />
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.tag && (
                <span
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    padding: '2px 6px',
                    borderRadius: 4,
                    background: isActive ? 'var(--brand-primary)' : 'var(--bg-subtle)',
                    color: isActive ? '#ffffff' : 'var(--text-muted)',
                  }}
                >
                  {item.tag}
                </span>
              )}
            </Link>
          )
        })}

        <div className="nav-section-label" style={{ marginTop: 14 }}>Infrastructure</div>
        {adminNav.map(item => {
          const Icon = item.icon
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={16} strokeWidth={isActive ? 2.5 : 2} />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="sidebar-footer">
        <div style={{ padding: '10px 12px', background: 'var(--bg-subtle)', borderRadius: 8, fontSize: 11, color: 'var(--text-muted)' }}>
          <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>Razorpay AI Builder</div>
          <div>All Invariant Guarantees Verified</div>
        </div>
      </div>
    </aside>
  )
}
