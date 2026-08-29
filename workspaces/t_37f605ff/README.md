# Compliance-as-Code: Automated Regulatory Testing Platform

A comprehensive compliance automation framework supporting **SOC2, HIPAA, GDPR, and PCI-DSS** with policy-as-code, evidence collection, drift detection, and audit reporting.

## Features

- **Policy Library** — 13 compliance controls across 4 frameworks (SOC2, HIPAA, GDPR, PCI-DSS)
- **Automated Evidence Collection** — Configuration snapshots, environment variables, log analysis
- **Drift Detection** — Compare current state against compliance baselines
- **Risk Scoring Engine** — Quantify compliance risk with weighted severity scoring
- **Remediation Playbooks** — Step-by-step guided remediation for each control failure
- **Continuous Monitoring** — Scheduled compliance checks with alerting
- **Cloud Integrations** — AWS Config, Azure Policy, GCP Security Command Center
- **Audit Reports** — JSON and Markdown output formats
- **CLI** — Full command-line interface with rich terminal output

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run compliance evaluation
compliance evaluate --framework SOC2

# Detect drift from baseline
compliance detect-drift --baseline baseline.json --current current.json

# Calculate risk score
compliance risk-score --framework HIPAA

# Generate remediation plan
compliance remediate --framework PCI-DSS

# Check cloud compliance
compliance cloud-compliance --provider aws

# Generate audit report
compliance audit --output ./reports
```

## Architecture

```
compliance_as_code/
├── engine.py        # Core compliance engine and data models
├── policies/        # Compliance control implementations
│   └── __init__.py  # SOC2, HIPAA, GDPR, PCI-DSS controls
├── evidence/        # Automated evidence collection
│   └── __init__.py  # Config, environment, log collectors
├── drift.py         # Drift detection engine
├── risk.py          # Risk scoring engine
├── remediation.py   # Remediation playbooks
├── monitor.py       # Continuous compliance monitoring
├── cloud.py         # Cloud provider integrations
├── reports.py       # Audit report generation
└── cli.py           # Command-line interface
```

## Compliance Frameworks

### SOC2 (4 controls)
- CC6.1 — Logical Access Controls
- CC6.7 — Encryption at Rest
- CC8.1 — Change Management
- CC7.4 — Incident Response

### HIPAA (2 controls)
- 164.312(a)(1) — Access Control
- 164.404 — Breach Notification

### GDPR (3 controls)
- Art. 7 — Conditions for Consent
- Art. 17 — Right to Erasure
- Art. 20 — Data Portability

### PCI-DSS (4 controls)
- Req 1 — Firewall Configuration
- Req 4 — Encrypt Transmission
- Req 6 — Secure Systems
- Req 7 — Restrict Access

## License

MIT
