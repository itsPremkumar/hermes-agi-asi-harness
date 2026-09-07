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

---

## Security Audit Log

### 2026-09-07 Weekly Security Audit

**Audit Date:** 2026-09-07 (Monday)  
**Auditor:** Automated Security Audit (Cron)  
**Scope:** CodeQL, dependencies, branch protection, secrets, access controls

#### Findings Summary

| Category | Status | Details |
|----------|--------|---------|
| CodeQL Alerts | ⚠️ 100 open | 3 errors, 4 warnings, 93 notes |
| Secret Scanning | ✅ Clean | 0 alerts |
| Dependencies | ✅ Clean | 0 known vulnerabilities (pip-audit) |
| Branch Protection | ✅ Configured | Main branch protected, 4 required checks |
| CI Pipeline | ❌ Failing | Structure + Lint & Format failing on main |
| Dependabot Alerts | ❌ Disabled | Security alerts not enabled |
| Access Control | ✅ Minimal | 1 collaborator (admin) |
| Actions Secrets | ✅ None | No secrets configured |

#### Critical Findings

1. **Empty Exception Handlers (CWE-390)** — 32 instances of `except: pass` in production code
   - Can mask security-relevant failures
   - Affects: recovery.py, watchdog.py, safety_kernel.py, tool_env.py, skills.py, recon.py, process_guard.py, and others
   - Issue: [#27](https://github.com/itsPremkumar/hermes-agi-asi-harness/issues/27)

2. **Illegal Raise Statements** — 2 instances in `src/hermes/agi/recovery.py`
   - `raise` used outside of except block (lines 365, 508)
   - Issue: [#27](https://github.com/itsPremkumar/hermes-agi-asi-harness/issues/27)

3. **Dependabot Security Alerts Disabled** — No automated CVE alerts
   - Version updates active but security alerts disabled
   - Issue: [#28](https://github.com/itsPremkumar/hermes-agi-asi-harness/issues/28)

4. **CI Pipeline Failure** — Main branch has failing checks
   - Structure check: FAILED
   - Lint & Format: FAILED
   - Blocks all merges including Dependabot PRs
   - Issue: [#29](https://github.com/itsPremkumar/hermes-agi-asi-harness/issues/29)

#### Recommendations

1. **Immediate:** Fix empty exception handlers with proper logging/error handling
2. **Immediate:** Enable Dependabot security alerts in repository settings
3. **Immediate:** Fix CI pipeline failures on main branch
4. **Short-term:** Address CodeQL warnings (unused imports, unreachable statements)
5. **Ongoing:** Review and dismiss false-positive CodeQL notes

#### Audit History

| Date | CodeQL Alerts | Vulns | CI Status | Notes |
|------|---------------|-------|-----------|-------|
| 2026-09-07 | 100 open | 0 known | Failing | First weekly audit |
