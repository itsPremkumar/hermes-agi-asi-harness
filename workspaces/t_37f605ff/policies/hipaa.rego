package compliance.hipaa

import data.compliance.utils

# 164.312(a)(1) — Access Control
# Technical policies for ePHI access: unique users, emergency access, auto-logoff, encryption.
default allow_access_control = false

allow_access_control {
    input.unique_user_ids == true
    input.emergency_access_procedure == true
    input.auto_logoff_minutes > 0
    input.auto_logoff_minutes <= 30
    input.ephi_encrypted == true
}

warning_access_control {
    input.unique_user_ids == true
    input.ephi_encrypted == true
    not allow_access_control
}

deny_access_control {
    not input.unique_user_ids
}

# 164.404 — Notification to individuals
# Breach notification to individuals within 60 days.
default allow_breach_notification = false

allow_breach_notification {
    input.breach_notification_procedure == true
    utils.meets_sla(input.breach_notification_days, 60)
    input.breach_log_maintained == true
}

warning_breach_notification {
    input.breach_notification_procedure == true
    not allow_breach_notification
}

deny_breach_notification {
    not input.breach_notification_procedure
}

# 164.312(e)(1) — Transmission Security
# Encrypt ePHI during transmission over networks.
default allow_transmission_security = false

allow_transmission_security {
    input.ephi_encrypted_transit == true
    utils.is_tls_acceptable(input.tls_version)
}

deny_transmission_security {
    not input.ephi_encrypted_transit
}

# Aggregate HIPAA result
compliance_pass {
    allow_access_control
    allow_breach_notification
}
