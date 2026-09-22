"""
PayGuard AI — pytest conftest.py

Shared fixtures for all test modules.
All test data is SYNTHETIC. No real provider credentials used.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def fake_webhook_secret() -> str:
    """Deterministic webhook secret for tests."""
    return "test-webhook-secret-synthetic-payguard"


@pytest.fixture
def synthetic_marker() -> str:
    """Marker for all synthetic test data."""
    return "[SYNTHETIC-TEST-ONLY]"
