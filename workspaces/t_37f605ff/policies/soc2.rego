package compliance.soc2

import data.compliance.utils

# CC6.1 — Logical and physical access controls
# Logical access to system components is restricted through RBAC and least-privilege.
default allow_cc61 = false

allow_cc61 {
    input.rbac_enabled == true
    input.mfa_enforced == true
    input.access_reviews_conducted == true
}

# Partial compliance — warning state
warning_cc61 {
    input.rbac_enabled == true
    not allow_cc61
}

# Deny if no access controls at all
deny_cc61 {
    not input.rbac_enabled
    not input.mfa_enforced
}

# CC6.7 — Encryption of data at rest
# Data at rest is encrypted using industry-standard algorithms.
default allow_cc67 = false

allow_cc67 {
    input.encryption_at_rest == true
    utils.is_encryption_standard(input.encryption_algorithm)
}

warning_cc67 {
    input.encryption_at_rest == true
    not utils.is_encryption_standard(input.encryption_algorithm)
}

deny_cc67 {
    not input.encryption_at_rest
}

# CC8.1 — Change management and authorization
# System changes are authorized, tested, and approved before production.
default allow_cc81 = false

allow_cc81 {
    input.change_approval_required == true
    input.peer_review_required == true
    input.test_environment_separate == true
}

warning_cc81 {
    input.change_approval_required == true
    not allow_cc81
}

deny_cc81 {
    not input.change_approval_required
    not input.peer_review_required
}

# CC7.4 — Incident response and notification
# Entity responds to incidents with a plan and notifies within defined timelines.
default allow_cc74 = false

allow_cc74 {
    input.incident_response_plan == true
    input.ir_plan_tested == true
    utils.meets_sla(input.notification_sla_hours, 72)
}

warning_cc74 {
    input.incident_response_plan == true
    not allow_cc74
}

deny_cc74 {
    not input.incident_response_plan
}

# Aggregate SOC2 compliance result
compliance_result[result] {
    result := {
        "control_id": "SOC2-CC6.1",
        "status": status,
        "evidence": evidence,
    }
    status := "PASS" { allow_cc61 } else_ "WARNING" { warning_cc61 } else_ "FAIL"
    evidence := ["RBAC enabled", "MFA enforced", "Access reviews conducted"]
}

# Helper for conditional assignment
else_ default = else_
