"""QualityWatch — Data Quality Monitoring & Validation System."""
from qualitywatch.models import Rule, CheckResult, QualityProfile, Severity, Status
from qualitywatch.engine import run_rule
from qualitywatch.profiler import profile
from qualitywatch.scoring import compute_score, TrendTracker
from qualitywatch.alerter import AlertManager, Alert
from qualitywatch.dashboard import Dashboard

__version__ = "0.1.0"