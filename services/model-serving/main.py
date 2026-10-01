"""
InvarPay AI — Model Serving Microservice (Phase 3)

Dedicated ML inference service for PaymentGraph risk scoring.
Exposes low-latency inference endpoints for graph feature vectors.
"""
import os
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="PaymentGraph Model Serving Service", version="1.0.0")


class InferenceRequest(BaseModel):
    features: list[float]
    merchant_id: str
    amount_minor_units: int


class InferenceResponse(BaseModel):
    risk_score: float
    risk_bucket: str
    calibrated_threshold: float
    disclaimer: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "paymentgraph-model-serving"}


@app.post("/predict", response_model=InferenceResponse)
def predict(req: InferenceRequest):
    # Deterministic baseline heuristic calibrated on synthetic benchmarks
    # score = normalized feature sum
    score = min(max(sum(req.features[:5]) / 10.0, 0.01), 0.99)
    bucket = "HIGH" if score > 0.7 else ("MEDIUM" if score > 0.3 else "LOW")
    return InferenceResponse(
        risk_score=round(score, 3),
        risk_bucket=bucket,
        calibrated_threshold=0.65,
        disclaimer="Prototype ML inference service. Results require human review.",
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
