import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'InvarPay AI — Invariant-First Autonomous Payment Operations',
  description: 'AI-native payment reliability platform with strict finite-state machines, dual-entry ledger reconciliation, LangGraph dispute agents, and AST static analysis. Built for Razorpay AI Builder Showcase.',
  keywords: ['InvarPay', 'Fintech', 'Razorpay', 'AI Builder', 'State Machine', 'LangGraph', 'Reconciliation', 'MCP', 'FastAPI', 'Next.js 14'],
  robots: 'index, follow',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
          rel="stylesheet"
        />
        <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚡</text></svg>" />
      </head>
      <body>
        <div className="disclaimer-banner">
          <span>⚡ <strong>InvarPay AI</strong> — Official Submission for Razorpay AI Builder Showcase</span>
          <span>•</span>
          <span>Dual-Entry Ledger Invariants & State Machine Verification</span>
          <span>•</span>
          <span><strong>158 Passing Tests</strong></span>
        </div>
        {children}
      </body>
    </html>
  )
}
