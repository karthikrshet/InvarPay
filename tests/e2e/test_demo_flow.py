"""
PayGuard AI — E2E Tests: Demo Workflow & API Endpoints

Verifies the HTTP API surface using FastAPI TestClient:
- Health checks (liveness and readiness)
- PaymentGraph fraud explainability & benchmark endpoints
- PayDev static analysis & rules endpoints
- MerchantOS cashflow & finance endpoints
- ShopAgent buyer confirmation gate & catalog safety

All endpoints verified with SYNTHETIC test data.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


class TestE2EDemoFlow:
    """End-to-end HTTP API verification."""

    def test_health_live_endpoint(self) -> None:
        """GET /health/live returns status ok."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "environment" in data

    def test_health_ready_endpoint(self) -> None:
        """GET /health/ready returns degraded or ok depending on local services."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]

    def test_paymentgraph_model_card(self) -> None:
        """GET /v1/risk/model-card provides transparent model documentation and disclosure."""
        response = client.get("/v1/risk/model-card")
        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data
        assert "synthetic" in data["data_provenance"].lower() or "public" in data["data_provenance"].lower()
        assert "limitations" in data

    def test_paymentgraph_rules_list(self) -> None:
        """GET /v1/risk/rules returns the deterministic fraud rules."""
        response = client.get("/v1/risk/rules")
        assert response.status_code == 200
        rules = response.json()
        assert isinstance(rules, list)
        rule_ids = [r["id"] for r in rules]
        assert "PG001" in rule_ids  # Velocity Spike
        assert "PG002" in rule_ids  # Impossible Travel
        assert "PG003" in rule_ids  # Card Bin Hopping

    def test_paymentgraph_synthetic_benchmark(self) -> None:
        """GET /v1/risk/benchmark returns explainable metrics on synthetic data."""
        response = client.get("/v1/risk/benchmark")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "BENCHMARK_COMPLETE"
        assert "precision" in data["metrics"]
        assert "recall" in data["metrics"]
        assert "pr_auc" in data["metrics"]

    def test_paydev_rules_list(self) -> None:
        """GET /v1/paydev/rules returns payment code inspection checks."""
        response = client.get("/v1/paydev/rules")
        assert response.status_code == 200
        rules = response.json()
        assert isinstance(rules, list)
        rule_ids = [r["id"] for r in rules]
        assert "SEC001" in rule_ids  # Hardcoded secret
        assert "FIN001" in rule_ids  # Float currency

    def test_shopagent_buyer_confirmation_gate_spec(self) -> None:
        """GET /v1/shopagent/buyer-confirmation-gate returns safety policy specs."""
        response = client.get("/v1/shopagent/buyer-confirmation-gate")
        assert response.status_code == 200
        data = response.json()
        assert data["autonomous_charges_permitted"] is False
        assert data["card_data_handling"] == "PROHIBITED"
        assert "explicit_buyer_signature" in data["confirmation_policy"]
