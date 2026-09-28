export interface PaymentAttempt {
  id: string
  organization_id: string
  order_id: string
  amount: number
  currency: string
  status: 'created' | 'initiated' | 'pending' | 'authorized' | 'captured' | 'failed' | 'cancelled' | 'unknown'
  provider: string
  provider_payment_id?: string
  created_at?: string
}

export interface RecoveryRecommendation {
  action: string
  safety: string
  reason: string
  requires_approval: boolean
  estimated_risk: string
}

export interface RiskAssessment {
  payment_attempt_id: string
  risk_level: string
  composite_score: number
  explanation: string
  requires_human_review: boolean
}
