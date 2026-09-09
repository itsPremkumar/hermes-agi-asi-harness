# AI Governance & Ethics Framework

> Policy engine, risk management, ethics review, and audit trail for AI systems.

## Features

- **PolicyEngine** — Register, enable, disable, evaluate AI governance policies
- **RiskAssessor** — Add risk assessments, calculate risk levels (low/medium/high/critical)
- **EthicsReviewer** — Create ethics reviews, approve/reject, add findings and recommendations
- **AuditLogger** — Log all actions with actor, resource, timestamp
- **Governance Facade** — Unified interface with compliance reporting

## Quick Start

```python
from governance import Governance, Policy, RiskAssessment

g = Governance()

# Register policies
g.policies.register(Policy(id="1", name="Data Privacy", description="Protect PII", category="privacy", severity="high"))

# Add risk assessments
g.risks.add(RiskAssessment(id="1", title="Data Breach", likelihood="high", impact="critical", risk_level="critical"))

# Generate compliance report
report = g.compliance_report()
print(report)
```

## Module Structure

```
src/governance/
├── __init__.py          # Governance facade + re-exports
├── policy_engine.py     # PolicyEngine, Policy, ComplianceCheck
├── risk_assessor.py     # RiskAssessor, RiskAssessment
├── ethics_reviewer.py   # EthicsReviewer, EthicsReview
└── audit.py             # AuditLogger, AuditTrail
```

## Running Tests

```bash
python -m pytest tests/ -v
```

## License

MIT
