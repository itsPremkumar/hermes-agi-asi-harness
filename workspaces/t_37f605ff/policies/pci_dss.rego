package compliance.pci_dss

import data.compliance.utils

# Req 1 — Install and maintain a firewall configuration
# Restrict connections between untrusted networks and cardholder data environment.
default allow_firewall = false

allow_firewall {
    input.firewall_enabled == true
    input.default_deny_policy == true
    input.firewall_rules_reviewed == true
}

warning_firewall {
    input.firewall_enabled == true
    not allow_firewall
}

deny_firewall {
    not input.firewall_enabled
}

# Req 4 — Encrypt transmission of cardholder data
# Use strong cryptography for transmission over open, public networks.
default allow_transmission_encryption = false

allow_transmission_encryption {
    utils.is_tls_acceptable(input.tls_version)
    input.weak_protocols_disabled == true
    input.certificate_valid == true
}

warning_transmission_encryption {
    utils.is_tls_acceptable(input.tls_version)
    not allow_transmission_encryption
}

deny_transmission_encryption {
    not utils.is_tls_acceptable(input.tls_version)
}

# Req 6 — Develop and maintain secure systems
# Install security patches and follow secure development practices.
default allow_secure_systems = false

allow_secure_systems {
    utils.meets_sla(input.patch_sla_days, 30)
    input.vulnerability_scanning == true
    input.secure_development_practices == true
}

warning_secure_systems {
    input.vulnerability_scanning == true
    not allow_secure_systems
}

deny_secure_systems {
    not input.vulnerability_scanning
}

# Req 7 — Restrict access to cardholder data
# Limit access using need-to-know principles.
default allow_access_restriction = false

allow_access_restriction {
    input.rbac_enabled == true
    input.need_to_know_enforced == true
    utils.meets_review_frequency(input.access_review_frequency_days, 90)
}

warning_access_restriction {
    input.rbac_enabled == true
    not allow_access_restriction
}

deny_access_restriction {
    not input.rbac_enabled
}

# Aggregate PCI-DSS result
compliance_pass {
    allow_firewall
    allow_transmission_encryption
    allow_secure_systems
    allow_access_restriction
}
