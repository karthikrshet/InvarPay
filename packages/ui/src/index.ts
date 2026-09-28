/**
 * PayGuard AI Shared UI Tokens & Utilities
 */

export const colors = {
  bg: '#0a0d14',
  cardBg: 'rgba(255, 255, 255, 0.03)',
  border: 'rgba(255, 255, 255, 0.08)',
  textPrimary: '#ffffff',
  textSecondary: '#94a3b8',
  status: {
    captured: '#10b981',
    authorized: '#3b82f6',
    pending: '#6366f1',
    initiated: '#8b5cf6',
    created: '#64748b',
    failed: '#ef4444',
    cancelled: '#64748b',
    unknown: '#f59e0b',
  },
}

export function formatMinorUnits(amount: number, currency: string = 'INR'): string {
  const units = (amount / 100).toFixed(2)
  return `${currency} ${units}`
}
