# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in InvarPay AI, please report it responsibly:

**Email:** security@invarpay.org  
**Response time:** We aim to respond within 48 hours.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact assessment
- Any suggested mitigations

Do **not** open a public GitHub issue for security vulnerabilities.

## Scope

In scope:
- Authentication bypass
- Cross-tenant data access
- Webhook signature bypass
- Payment state manipulation
- Credential exposure
- Injection vulnerabilities (SQL, prompt)

Out of scope:
- Rate limiting (not yet implemented in Phase 1)
- DDoS attacks
- Social engineering

## Data Handling

- No real payment credentials (card numbers, CVVs, UPI PINs) are stored
- Provider credentials are encrypted at rest (AES-256)
- All webhook secrets are hashed or encrypted
- API key full values are shown only once on creation and hashed for storage
- Audit logs are append-only with hash chaining
- Test-mode Razorpay credentials (rzp_test_*) are never stored in code

## Responsible Disclosure

We follow a coordinated disclosure process:
1. You report the vulnerability privately
2. We acknowledge within 48 hours
3. We work on a fix (typically within 30 days for critical issues)
4. We release the fix and publicly credit the reporter (if desired)
5. You may publish your findings after the fix is released

Thank you for helping keep InvarPay AI secure.
