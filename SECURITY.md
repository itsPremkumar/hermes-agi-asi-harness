# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x | ✅ |
| 0.x | ❌ |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by emailing the maintainers at the contact information in the repository. Do NOT open a public issue for security vulnerabilities.

We will acknowledge receipt within 48 hours and provide a detailed response within 7 days.

## Security Measures

This project implements the following security measures:

### Code Security
- **Bandit** — Static analysis for common Python security issues
- **pip-audit** — Scans dependencies for known vulnerabilities
- **Pre-commit hooks** — Detect private keys, executables, and merge conflicts
- **Type checking** — mypy for catching type-related bugs

### CI/CD Security
- **Dependency scanning** — Automated vulnerability scanning in CI
- **Secret detection** — Pre-commit hooks detect committed secrets
- **Container scanning** — Docker images scanned for CVEs
- **Signed releases** — All releases signed with Sigstore

### Runtime Security
- **Non-root containers** — Docker runs as non-root user
- **Health checks** — Liveness and readiness probes
- **Circuit breakers** — Prevent cascade failures
- **Graceful degradation** — Reduced functionality instead of total failure

### Access Control
- **Principle of least privilege** — Minimal permissions for each component
- **Environment separation** — Staging and production isolated
- **Audit logging** — All actions logged for review

## Security Best Practices for Contributors

1. Never commit secrets, tokens, or credentials
2. Use environment variables for sensitive configuration
3. Keep dependencies updated
4. Follow the principle of least privilege
5. Write tests for security-critical code
6. Review security implications of new features

## Automated Security Scanning

```bash
# Run security scans locally
make security

# Or directly
bandit -r src/ -c pyproject.toml
pip-audit -r requirements.txt
```

## Security Response Process

1. **Receive** — Acknowledge vulnerability report within 48 hours
2. **Assess** — Determine severity and impact within 7 days
3. **Fix** — Develop and test a patch
4. **Disclose** — Release patch and publish advisory
5. **Credit** — Acknowledge the reporter (with permission)

## Dependencies

We monitor our dependencies for security vulnerabilities using:
- GitHub Dependabot
- pip-audit in CI
- Manual review of dependency updates
