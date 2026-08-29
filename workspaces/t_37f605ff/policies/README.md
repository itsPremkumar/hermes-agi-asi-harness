# OpenPolicyAgent Rego Policies for Compliance-as-Code

This directory contains Rego policy definitions for OpenPolicyAgent (OPA) integration.
These policies mirror the Python controls and can be used standalone with OPA or via the compliance engine.

## Structure

```
policies/
├── soc2.rego       # SOC2 Trust Services Criteria
├── hipaa.rego      # HIPAA Security Rule
├── gdpr.rego       # GDPR Articles
├── pci_dss.rego    # PCI-DSS Requirements
└── utils.rego      # Shared helper functions
```

## Usage with OPA

```bash
# Evaluate a policy
eval 'data.compliance.soc2.allow' --data policies/soc2.rego --input input.json

# Run OPA server
opa run --server policies/

# Test policies
opa test policies/ -v
```

## Integration

The Python compliance engine can call OPA for policy evaluation:

```python
from compliance_as_code.engine import ComplianceEngine
engine = ComplianceEngine(policy_dir="policies/")
report = engine.evaluate(ComplianceFramework.SOC2, context)
```
