"""
Phase 4 tests: PayDev code analysis engine.
Tests secret detection, float currency, and webhook verification checks.
"""
from __future__ import annotations

import os
import tempfile
import textwrap
from pathlib import Path

import pytest

from modules.paydev.analyzer import _check_file, analyze_repository


class TestSecretDetection:
    """Test that secret detection works on synthetic code samples."""

    def _write_temp(self, content: str, suffix: str = ".py") -> Path:
        """Write content to a temp file and return path."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, delete=False, dir=tempfile.gettempdir()
        )
        tmp.write(content)
        tmp.close()
        return Path(tmp.name)

    def _root_for(self, path: Path) -> Path:
        return path.parent

    def test_live_razorpay_key_detected(self) -> None:
        """rzp_live_ key must be flagged as CRITICAL."""
        code = 'key = "rzp_live_FAKEKEYFORTEST1234"\n'
        path = self._write_temp(code)
        try:
            issues = _check_file(path, self._root_for(path))
            assert any(i.severity == "CRITICAL" and "Razorpay" in i.description for i in issues), \
                "Live Razorpay key not detected"
        finally:
            os.unlink(path)

    def test_test_key_not_flagged(self) -> None:
        """rzp_test_ keys are OK in test code."""
        code = 'key = "rzp_test_SAFETESTKEY1234"\n'
        path = self._write_temp(code)
        try:
            issues = _check_file(path, self._root_for(path))
            # rzp_test_ should not be flagged (only rzp_live_)
            critical = [i for i in issues if i.severity == "CRITICAL" and "live" in i.description.lower()]
            assert not critical, f"Test key incorrectly flagged as critical: {critical}"
        finally:
            os.unlink(path)

    def test_float_currency_detected(self) -> None:
        """Float currency amounts must be flagged."""
        code = "amount = 499.99  # This is wrong\n"
        path = self._write_temp(code)
        try:
            issues = _check_file(path, self._root_for(path))
            assert any(i.category == "float_currency" for i in issues), \
                "Float currency not detected"
        finally:
            os.unlink(path)

    def test_integer_currency_not_flagged(self) -> None:
        """Integer currency amounts should not be flagged."""
        code = "amount_paise = 49999  # Correct: integers\n"
        path = self._write_temp(code)
        try:
            issues = _check_file(path, self._root_for(path))
            float_issues = [i for i in issues if i.category == "float_currency"]
            assert not float_issues, f"Integer currency incorrectly flagged: {float_issues}"
        finally:
            os.unlink(path)

    def test_webhook_without_verification_flagged(self) -> None:
        """Webhook handler without signature verification must be flagged."""
        code = textwrap.dedent("""
        def handle_webhook(request):
            data = request.json()
            process(data)
        """)
        path = self._write_temp(code)
        try:
            issues = _check_file(path, self._root_for(path))
            assert any(i.category == "missing_webhook_verification" for i in issues), \
                "Missing webhook verification not detected"
        finally:
            os.unlink(path)

    def test_verified_webhook_not_flagged(self) -> None:
        """Webhook handler with HMAC verification should pass."""
        code = textwrap.dedent("""
        import hmac, hashlib
        def handle_webhook(request, raw_body, signature, secret):
            expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, signature):
                raise ValueError("Invalid signature")
            data = json.loads(raw_body)
        """)
        path = self._write_temp(code)
        try:
            issues = _check_file(path, self._root_for(path))
            sig_issues = [i for i in issues if i.category == "missing_webhook_verification"]
            assert not sig_issues, f"Verified webhook incorrectly flagged: {sig_issues}"
        finally:
            os.unlink(path)


class TestRepositoryAnalysis:
    """Test full repository analysis."""

    def test_empty_dir_returns_zero_issues(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = analyze_repository(tmpdir)
            assert report.files_analyzed == 0
            assert len(report.issues) == 0

    def test_nonexistent_path_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            analyze_repository("/nonexistent/path/xyz")

    def test_report_has_disclaimer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            report = analyze_repository(tmpdir)
            assert "READ-ONLY" in report.disclaimer or "proposal" in report.disclaimer.lower()
