package compliance.gdpr

import data.compliance.utils

# Art. 7 — Conditions for consent
# Controller must demonstrate data subject consent.
default allow_consent = false

allow_consent {
    input.consent_records_maintained == true
    input.consent_withdrawal_mechanism == true
    input.explicit_consent_required == true
}

warning_consent {
    input.consent_records_maintained == true
    not allow_consent
}

deny_consent {
    not input.consent_records_maintained
}

# Art. 17 — Right to erasure (right to be forgotten)
# Data subject can request erasure without undue delay.
default allow_erasure = false

allow_erasure {
    input.erasure_procedure == true
    utils.meets_sla(input.erasure_timeline_days, 30)
    input.erasure_verification == true
}

warning_erasure {
    input.erasure_procedure == true
    not allow_erasure
}

deny_erasure {
    not input.erasure_procedure
}

# Art. 20 — Right to data portability
# Data subject receives personal data in structured, machine-readable format.
default allow_portability = false

allow_portability {
    input.data_export_api == true
    count(input.data_export_formats) >= 2
    input.automated_export == true
}

warning_portability {
    input.data_export_api == true
    not allow_portability
}

deny_portability {
    not input.data_export_api
    count(input.data_export_formats) == 0
}

# Art. 25 — Data protection by design and default
# Implement appropriate technical measures.
default allow_privacy_by_design = false

allow_privacy_by_design {
    input.data_minimization == true
    input.pseudonymization_enabled == true
    input.privacy_impact_assessment == true
}

# Aggregate GDPR result
compliance_pass {
    allow_consent
    allow_erasure
    allow_portability
}
