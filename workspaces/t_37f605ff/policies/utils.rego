package compliance.utils

# Helper functions for compliance policies

# Check if encryption meets minimum standard
is_encryption_standard(algorithm) {
    algorithm == "AES-256-GCM"
}

is_encryption_standard(algorithm) {
    algorithm == "AES-256"
}

is_encryption_standard(algorithm) {
    algorithm == "ChaCha20-Poly1305"
}

# Check if TLS version is acceptable (1.2+)
is_tls_acceptable(version) {
    version == "1.2"
}

is_tls_acceptable(version) {
    version == "1.3"
}

# Check if SLA meets requirement (days)
meets_sla(actual_days, max_days) {
    actual_days <= max_days
}

# Check if review frequency is acceptable
meets_review_frequency(actual_days, max_days) {
    actual_days <= max_days
}

# Severity weights for risk scoring
severity_weight(severity) = 10 { severity == "CRITICAL" }
severity_weight(severity) = 7 { severity == "HIGH" }
severity_weight(severity) = 4 { severity == "MEDIUM" }
severity_weight(severity) = 2 { severity == "LOW" }
severity_weight(severity) = 1 { severity == "INFO" }
