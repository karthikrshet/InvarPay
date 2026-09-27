'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

export function Sidebar() {
  const pathname = usePathname()

  const coreNav = [
    { href: '/', icon: '⬡', label: 'Dashboard' },
    { href: '/payments', icon: '₹', label: 'Payments' },
    { href: '/orders', icon: '📋', label: 'Orders' },
    { href: '/investigations', icon: '🔍', label: 'Investigations' },
    { href: '/audit', icon: '🔒', label: 'Audit Log' },
  ]

  const moduleNav = [
    { href: '/risk', icon: '🛡️', label: 'PaymentGraph' },
    { href: '/paydev', icon: '⚡', label: 'PayDev' },
    { href: '/merchantos', icon: '📊', label: 'MerchantOS' },
    { href: '/shop', icon: '🛒', label: 'ShopAgent' },
  ]

  const adminNav = [
    { href: '/settings', icon: '⚙️', label: 'Settings & Adapters' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-mark">
          <div className="logo-icon">⬡</div>
          <div>
            <div className="logo-text">InvarPay AI</div>
          </div>
        </div>
        <div style={{ marginTop: 8, display: 'flex', gap: 6 }}>
          <span className="logo-badge">TEST MODE</span>
          <span className="logo-badge">OPEN SOURCE</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Core Reliability</div>
        {coreNav.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item ${pathname === item.href ? 'active' : ''}`}
          >
            <span style={{ fontSize: 16 }}>{item.icon}</span>
            {item.label}
          </Link>
        ))}

        <div className="nav-section-label" style={{ marginTop: 16 }}>AI Modules</div>
        {moduleNav.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item ${pathname === item.href ? 'active' : ''}`}
          >
            <span style={{ fontSize: 16 }}>{item.icon}</span>
            {item.label}
          </Link>
        ))}

        <div className="nav-section-label" style={{ marginTop: 16 }}>Configuration</div>
        {adminNav.map(item => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item ${pathname === item.href ? 'active' : ''}`}
          >
            <span style={{ fontSize: 16 }}>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  )
}
