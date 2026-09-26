import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'InvarPay AI — Financial Operations Platform',
  description: 'AI-native payment reliability, fraud intelligence, and financial operations. Open-source, independent platform. Razorpay adapter runs in TEST MODE only.',
  keywords: ['invarpay', 'payments', 'financial operations', 'AI', 'fraud detection', 'payment reliability'],
  robots: 'noindex',  // Internal dashboard — not for public indexing
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
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        <div className="disclaimer-banner">
          ⚠️ InvarPay AI — Independent open-source platform. Not affiliated with Razorpay.
          Payment provider operates in <strong>TEST MODE</strong> only. All demo data is <strong>SYNTHETIC</strong>.
        </div>
        {children}
      </body>
    </html>
  )
}
