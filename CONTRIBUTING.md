# Contributing to InvarPay AI

Thank you for your interest in contributing to InvarPay AI!

## Before You Start

1. Read [README.md](README.md) to understand the project
2. Read [docs/security/threat-model.md](docs/security/threat-model.md)
3. Read [docs/architecture/payment-state-machine.md](docs/architecture/payment-state-machine.md)
4. Understand the safety invariants — these are non-negotiable

## Development Setup

```bash
cp .env.example .env
make setup
make dev
```

## Running Tests

```bash
make test            # All tests
make test-unit       # Unit tests only
make test-security   # Security tests
make test-chaos      # Chaos tests
```

**All tests must pass before submitting a PR.**

## Code Standards

- Python: PEP 8, type hints required, `ruff` for linting
- TypeScript: ESLint, strict mode enabled
- No commented-out code
- No `TODO` without a linked issue
- Tests required for new features

## Security Requirements (Non-Negotiable)

- Never commit real credentials (API keys, secrets, passwords)
- Never store or log card data (PAN, CVV, expiry)
- All new endpoints must have tenant isolation tests
- New provider adapters must implement signature verification
- Agent tools must pass through the policy engine
- No LLM output may directly mutate payment state

## PR Process

1. Create a feature branch from `main`
2. Write tests first (TDD encouraged)
3. Run `make lint` and `make test`
4. Submit PR with description of changes
5. Wait for code review (at least 1 approval required)

## License

By contributing, you agree your contributions are licensed under the MIT license.
