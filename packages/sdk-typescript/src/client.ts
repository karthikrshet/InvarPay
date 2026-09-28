import { PaymentAttempt, RecoveryRecommendation, RiskAssessment } from './types'

export class InvarPayClient {
  private apiUrl: string
  private apiKey?: string

  constructor(options?: { apiUrl?: string; apiKey?: string }) {
    this.apiUrl = (options?.apiUrl || 'http://localhost:8000').replace(/\/$/, '')
    this.apiKey = options?.apiKey
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'User-Agent': 'InvarPay-TS-SDK/1.0.0',
    }
    if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey
    }

    const res = await fetch(`${this.apiUrl}${path}`, {
      ...options,
      headers: { ...headers, ...options?.headers },
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(`InvarPay API Error ${res.status}: ${JSON.stringify(err)}`)
    }

    return res.json()
  }

  async getPayment(paymentId: string): Promise<PaymentAttempt> {
    return this.request<PaymentAttempt>(`/v1/payments/${paymentId}`)
  }

  async getRecoveryRecommendation(paymentId: string): Promise<RecoveryRecommendation> {
    return this.request<RecoveryRecommendation>(`/v1/payments/${paymentId}/recovery`)
  }

  async getRiskAssessment(paymentId: string): Promise<RiskAssessment> {
    return this.request<RiskAssessment>(`/v1/risk/${paymentId}`)
  }
}

// Backwards-compatible alias
export const PayGuardClient = InvarPayClient
