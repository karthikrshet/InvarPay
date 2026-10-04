"""
InvarPay AI — Phase 4: PayDev Code Analysis Engine

Analyzes repository code for payment integration issues.
Produces PROPOSED diffs — never modifies code without approval.

Safety constraints:
- Read-only file access (no writes, no shell execution)
- SSRF protection: only local filesystem paths allowed
- Max file size: 512KB per file
- Max files: 1000 per analysis run
- All proposed changes require explicit user approval

Detects:
- Hardcoded credentials (live provider keys, AWS access keys, etc.)
- Missing webhook signature verification
- Float arithmetic for currency amounts (use integers)
- Missing idempotency keys
- Insecure error logging (logging PAN/CVV)
"""
from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 512 * 1024  # 512KB
MAX_FILES = 1000
ALLOWED_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}

# Secret patterns — these should never appear in source code
SECRET_PATTERNS = [
    (re.compile(r"rzp_" + r"live_[A-Za-z0-9]+"), "Razorpay live key"),
    (re.compile(r"sk_" + r"live_[A-Za-z0-9]+"), "Stripe live key"),
    (re.compile(r"AK" + r"IA[A-Z0-9]{16}"), "AWS Access Key ID"),
    (re.compile(r"-----BEGIN (RSA|EC|DSA) PRIVATE KEY-----"), "Private key"),
    (re.compile(r"(?i)(password|passwd|pwd)\s*=\s*[\"'][^\"']{6,}[\"']"), "Hardcoded password"),
    (re.compile(r"(?i)(secret|api_key)\s*=\s*[\"'][^\"']{8,}[\"']"), "Hardcoded secret"),
]

# Float currency patterns
FLOAT_CURRENCY_PATTERN = re.compile(
    r"(amount|price|cost|fee|tax|total)\s*=\s*\d+\.\d+",
    re.IGNORECASE
)

# Missing webhook verification patterns
WEBHOOK_WITHOUT_VERIFY = re.compile(
    r"webhook.*payload|payload.*webhook",
    re.IGNORECASE
)


@dataclass
class CodeIssue:
    """A detected issue in the payment integration code."""
    severity: str  # CRITICAL / HIGH / MEDIUM / LOW / INFO
    category: str  # credential_exposure / missing_verification / float_currency / etc.
    file_path: str
    line_number: Optional[int]
    line_content: Optional[str]
    description: str
    suggested_fix: Optional[str] = None
    reference: Optional[str] = None


@dataclass
class AnalysisReport:
    """
    Complete code analysis report.
    All fixes are PROPOSALS — require user approval to apply.
    """
    root_path: str
    files_analyzed: int
    issues: list[CodeIssue] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    proposed_diffs: list[dict] = field(default_factory=list)
    disclaimer: str = (
        "PayDev analysis is read-only. All suggested changes are proposals. "
        "No files are modified without explicit user approval."
    )

    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "CRITICAL")

    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "HIGH")


def _is_safe_path(path: Path, root: Path) -> bool:
    """SSRF protection: ensure path is within the declared root."""
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _check_file(file_path: Path, root: Path) -> list[CodeIssue]:
    """Analyze a single file for payment integration issues."""
    issues: list[CodeIssue] = []

    if not _is_safe_path(file_path, root):
        return []

    if file_path.stat().st_size > MAX_FILE_BYTES:
        return []

    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    lines = content.splitlines()
    rel_path = str(file_path.relative_to(root))

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Check for hardcoded secrets
        for pattern, label in SECRET_PATTERNS:
            if pattern.search(stripped):
                issues.append(CodeIssue(
                    severity="CRITICAL",
                    category="credential_exposure",
                    file_path=rel_path,
                    line_number=i,
                    line_content=stripped[:120],
                    description=f"Possible {label} hardcoded in source",
                    suggested_fix="Use environment variables or a secrets manager",
                    reference="https://owasp.org/Top10/A02_2021-Cryptographic_Failures/",
                ))

        # Float currency
        if FLOAT_CURRENCY_PATTERN.search(stripped):
            issues.append(CodeIssue(
                severity="HIGH",
                category="float_currency",
                file_path=rel_path,
                line_number=i,
                line_content=stripped[:120],
                description="Currency amount stored as float — use integer paise/cents",
                suggested_fix="Convert to int: amount_paise = int(amount_rupees * 100)",
                reference="https://martinfowler.com/eaaCatalog/money.html",
            ))

        # Idempotency key missing near payment initiation
        if "initiate_payment" in stripped or "create_payment" in stripped:
            if "idempotency" not in content.lower():
                issues.append(CodeIssue(
                    severity="HIGH",
                    category="missing_idempotency",
                    file_path=rel_path,
                    line_number=i,
                    line_content=stripped[:120],
                    description="Payment initiation without idempotency key detected",
                    suggested_fix="Add idempotency_key to prevent duplicate payments on retry",
                ))

    # Python AST analysis for signature verification
    if file_path.suffix == ".py":
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_src = "".join(lines[node.lineno-1:node.end_lineno])
                    if ("webhook" in node.name.lower() and
                            "verify" not in func_src.lower() and
                            "signature" not in func_src.lower() and
                            "hmac" not in func_src.lower()):
                        issues.append(CodeIssue(
                            severity="HIGH",
                            category="missing_webhook_verification",
                            file_path=rel_path,
                            line_number=node.lineno,
                            line_content=f"def {node.name}(...)",
                            description=f"Webhook handler '{node.name}' may be missing signature verification",
                            suggested_fix="Verify HMAC-SHA256 signature on raw body BEFORE parsing JSON",
                        ))
        except SyntaxError:
            pass

    return issues


def analyze_repository(root_path: str) -> AnalysisReport:
    """
    Analyze a repository for payment integration issues.
    Read-only. No files are modified.
    """
    root = Path(root_path).resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Root path does not exist or is not a directory: {root_path}")

    report = AnalysisReport(root_path=root_path, files_analyzed=0)
    file_count = 0

    for file_path in root.rglob("*"):
        if file_count >= MAX_FILES:
            break
        if not file_path.is_file():
            continue
        if file_path.suffix not in ALLOWED_EXTENSIONS:
            continue
        # Skip vendor/node_modules/venv
        parts = set(file_path.parts)
        if parts & {"node_modules", "venv", ".venv", "__pycache__", ".git", "vendor"}:
            continue

        issues = _check_file(file_path, root)
        report.issues.extend(issues)
        file_count += 1

    report.files_analyzed = file_count
    report.summary = {
        "files_analyzed": file_count,
        "total_issues": len(report.issues),
        "critical": report.critical_count(),
        "high": report.high_count(),
        "by_category": {},
    }
    for issue in report.issues:
        cat = issue.category
        report.summary["by_category"][cat] = report.summary["by_category"].get(cat, 0) + 1

    return report


def generate_unified_diff(original: str, modified: str, filename: str = "handler.py") -> str:
    """Generate a clean unified diff between original and remediated code."""
    import difflib
    orig_lines = original.splitlines(keepends=True)
    mod_lines = modified.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines, mod_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm=""
    )
    return "\n".join(diff)


def analyze_code_string(code: str, filename: str = "handler.py") -> dict:
    """
    Perform live AST and heuristic static analysis on a code string.
    Generates automated remediation and unified diff patch.
    """
    issues: list[dict] = []
    lines = code.splitlines()
    remediated_lines = list(lines)

    # 1. Check for hardcoded secrets
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        for pattern, label in SECRET_PATTERNS:
            match = pattern.search(stripped)
            if match:
                issues.append({
                    "id": f"SEC-{i}",
                    "severity": "CRITICAL",
                    "category": "credential_exposure",
                    "rule_id": "SEC001",
                    "line": i,
                    "line_content": stripped,
                    "description": f"Hardcoded credential detected ({label}). Never commit live secrets or API keys to source control.",
                    "suggested_fix": "Extract secret to environment variable using os.environ.get('RAZORPAY_KEY_ID')",
                    "reference": "CWE-798: Use of Hard-coded Credentials",
                })
                # Propose safe remediation in-place
                remediated_lines[i-1] = re.sub(
                    r"[\"'](rzp_live_[A-Za-z0-9]+|sk_live_[A-Za-z0-9]+|[A-Za-z0-9_\-]{20,})[\"']",
                    "os.environ.get('PAYMENT_PROVIDER_KEY', '')",
                    remediated_lines[i-1]
                )

        # 2. Float currency math
        if FLOAT_CURRENCY_PATTERN.search(stripped):
            issues.append({
                "id": f"FIN-{i}",
                "severity": "HIGH",
                "category": "float_currency",
                "rule_id": "FIN001",
                "line": i,
                "line_content": stripped,
                "description": "Floating-point currency calculation detected. Monetary values must use minor integer units (paise/cents) to avoid IEEE-754 precision loss.",
                "suggested_fix": "Store and compute amounts in integer paise: amount_paise = int(round(amount_rupees * 100))",
                "reference": "Martin Fowler: Money Pattern",
            })
            # Propose minor unit integer conversion
            remediated_lines[i-1] = re.sub(
                r"(\d+)\.(\d+)",
                lambda m: f"int({m.group(0)} * 100)  # Converted to integer minor units (paise)",
                remediated_lines[i-1]
            )

        # 3. Missing idempotency in payment calls
        if ("initiate_payment" in stripped or "create_payment" in stripped) and "idempotency" not in code.lower():
            issues.append({
                "id": f"IDEM-{i}",
                "severity": "HIGH",
                "category": "missing_idempotency",
                "rule_id": "IDEM001",
                "line": i,
                "line_content": stripped,
                "description": "Payment creation method invoked without idempotency key. Network retries will cause duplicate customer charges.",
                "suggested_fix": "Provide idempotency_key=str(uuid.uuid4()) to guarantee exactly-once payment processing.",
                "reference": "IETF Draft: Idempotency-Key HTTP Header Field",
            })

        # 4. Sensitive PAN / CVV logging check
        if any(term in stripped.lower() for term in ["cvv", "card_number", "pan", "expiry"]) and ("log" in stripped.lower() or "print" in stripped.lower()):
            issues.append({
                "id": f"PCI-{i}",
                "severity": "CRITICAL",
                "category": "pci_violation",
                "rule_id": "PCI001",
                "line": i,
                "line_content": stripped,
                "description": "Potential cardholder data (PAN/CVV) logged to console or logs. Violation of PCI-DSS Requirement 3.",
                "suggested_fix": "Mask card numbers: f'****-****-****-{card_number[-4:]}' and redact CVV.",
                "reference": "PCI-DSS v4.0 Requirement 3.3",
            })
            remediated_lines[i-1] = "# [REDACTED BY INVARPAY AST] Removed PCI-sensitive card data logging"

    # 5. Python AST analysis for Webhook Signature Verification
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_lines = lines[node.lineno-1:node.end_lineno or len(lines)]
                func_src = "\n".join(func_lines)
                if "webhook" in node.name.lower():
                    has_verify = any(tok in func_src.lower() for tok in ["verify", "signature", "hmac", "sha256"])
                    if not has_verify:
                        issues.append({
                            "id": f"SIG-{node.lineno}",
                            "severity": "CRITICAL",
                            "category": "missing_webhook_verification",
                            "rule_id": "SIG001",
                            "line": node.lineno,
                            "line_content": f"def {node.name}(...)",
                            "description": f"Webhook handler '{node.name}' processes payment callbacks without verifying HMAC-SHA256 signature against raw body bytes.",
                            "suggested_fix": "Verify HMAC signature before parsing JSON payload using hmac.compare_digest.",
                            "reference": "OWASP A02:2021 Cryptographic Failures",
                        })
    except SyntaxError as e:
        issues.append({
            "id": "SYNTAX-0",
            "severity": "MEDIUM",
            "category": "syntax_error",
            "rule_id": "SYN001",
            "line": e.lineno or 1,
            "line_content": e.text.strip() if e.text else "",
            "description": f"Python AST syntax error: {e.msg}",
            "suggested_fix": "Fix Python syntax formatting.",
            "reference": "Python AST Parser",
        })

    remediated_code = "\n".join(remediated_lines)
    diff = generate_unified_diff(code, remediated_code, filename)

    return {
        "filename": filename,
        "total_issues": len(issues),
        "critical_count": sum(1 for i in issues if i["severity"] == "CRITICAL"),
        "high_count": sum(1 for i in issues if i["severity"] == "HIGH"),
        "medium_count": sum(1 for i in issues if i["severity"] == "MEDIUM"),
        "issues": issues,
        "is_compliant": len(issues) == 0,
        "remediated_code": remediated_code if diff else None,
        "unified_diff": diff if diff else None,
    }

