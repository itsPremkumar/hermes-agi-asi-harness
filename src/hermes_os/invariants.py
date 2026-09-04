"""
HERMES SAFETY — 22 EXECUTABLE INVARIANTS
========================================
Each invariant is a callable predicate (state -> (ok, reason)),
replacing the previous dead-string list. State keys used:
action_type, action_args, principal, risk_level, taint_present,
human_approved, kill_switch, backup_exists, provenance, retrieval_ms...
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

Check = Callable[[Dict[str, Any]], Tuple[bool, str]]


def _ok() -> Tuple[bool, str]:
    return True, ""


def inv_no_destructive_without_approval(s: Dict[str, Any]) -> Tuple[bool, str]:
    if str(s.get("action_type", "")) in ("delete_file", "drop_database", "truncate_table", "format_disk"):
        if not s.get("human_approved"):
            return False, "Destructive action requires human approval"
    return _ok()


def inv_no_raw_system_destroy(s: Dict[str, Any]) -> Tuple[bool, str]:
    cmd = str((s.get("action_args") or {}).get("command", ""))[:500].lower()
    for sig in ("rm -rf /", "mkfs", "format-volume", "clear-disk", ":(){:|:&};:"):
        if sig in cmd:
            return False, f"System-destroy signature: {sig}"
    return _ok()


def inv_no_exfiltration(s: Dict[str, Any]) -> Tuple[bool, str]:
    cmd = str((s.get("action_args") or {}).get("command", ""))[:1000].lower()
    secrets = ("id_rsa", ".env", "passwd", "shadow", "sam")
    if ("curl" in cmd or "wget" in cmd or "nc " in cmd) and any(x in cmd for x in secrets):
        return False, "Credential exfiltration pattern"
    return _ok()


def inv_no_path_traversal_to_secrets(s: Dict[str, Any]) -> Tuple[bool, str]:
    blob = str(s.get("action_args", ""))[:2000]
    if "../../" in blob and any(x in blob for x in ("passwd", "shadow", "SAM", "id_rsa", ".env")):
        return False, "Path traversal toward secrets"
    return _ok()


def inv_no_remote_code_exec(s: Dict[str, Any]) -> Tuple[bool, str]:
    cmd = str((s.get("action_args") or {}).get("command", ""))[:1000].lower()
    if "invoke-expression" in cmd and ("iwr" in cmd or "irm" in cmd or "curl" in cmd):
        return False, "Remote-code cradle blocked"
    return _ok()


def inv_prompt_injection_screen(s: Dict[str, Any]) -> Tuple[bool, str]:
    blob = str(s.get("action_args", ""))[:4000].lower()
    for sig in ("ignore previous instructions", "ignore all instructions", "system prompt:", "jailbreak", "dan mode"):
        if sig in blob:
            return False, f"Possible prompt injection: '{sig}'"
    return _ok()


def inv_no_self_replication(s: Dict[str, Any]) -> Tuple[bool, str]:
    blob = (str(s.get("action_type", "")) + " " + str(s.get("action_args", "")))[:2000].lower()
    if ("replicate" in blob or "self-copy" in blob or "spawn replica" in blob) and not s.get("human_approved"):
        return False, "Self-replication requires multi-party review"
    return _ok()


def inv_corrigibility(s: Dict[str, Any]) -> Tuple[bool, str]:
    blob = str(s.get("action_args", ""))[:2000].lower()
    for sig in ("disable safety", "kill supervisor", "remove audit", "bypass gate"):
        if sig in blob:
            return False, f"Corrigibility threat: '{sig}'"
    return _ok()


def inv_taint_no_shell(s: Dict[str, Any]) -> Tuple[bool, str]:
    if s.get("taint_present") and str(s.get("action_type", "")) in ("execute_shell", "execute_python", "python_repl"):
        return False, "Tainted input into code execution"
    return _ok()


def inv_kill_switch(s: Dict[str, Any]) -> Tuple[bool, str]:
    if s.get("kill_switch"):
        return False, "KILL switch engaged — all mutating actions halted"
    return _ok()


def inv_human_approval_r6(s: Dict[str, Any]) -> Tuple[bool, str]:
    if str(s.get("risk_level", "medium")).lower() in ("critical",) and not s.get("human_approved"):
        if str(s.get("action_type", "")) not in ("read_file", "list_dir", "grep_search", "find_by_name"):
            return False, "Critical-risk action requires R6 human approval"
    return _ok()


def inv_provenance_required(s: Dict[str, Any]) -> Tuple[bool, str]:
    if s.get("require_provenance") and not s.get("provenance"):
        return False, "Knowledge item missing provenance"
    return _ok()


def inv_retrieval_latency(s: Dict[str, Any]) -> Tuple[bool, str]:
    ms = float(s.get("retrieval_ms", 0) or 0)
    if ms > 5000:
        return False, f"Retrieval too slow ({ms:.0f}ms)"
    return _ok()


def inv_backup_before_mutation(s: Dict[str, Any]) -> Tuple[bool, str]:
    if str(s.get("action_type", "")) in ("apply_patch", "edit_file", "write_file"):
        if s.get("require_backup") and not s.get("backup_exists"):
            return False, "Mutation requires backup/checkpoint first"
    return _ok()


def inv_no_test_tampering(s: Dict[str, Any]) -> Tuple[bool, str]:
    blob = str(s.get("action_args", ""))[:2000].lower()
    if "test_" in blob and ("skip" in blob or "assert true" in blob or "return 1.0" in blob):
        return False, "Test tampering / reward hacking signature"
    return _ok()


def inv_output_law(s: Dict[str, Any]) -> Tuple[bool, str]:
    if s.get("require_diff") and s.get("has_diff") is False:
        return False, "OUTPUT LAW: no observable diff"
    return _ok()


def inv_scope_containment(s: Dict[str, Any]) -> Tuple[bool, str]:
    blob = str(s.get("action_args", ""))[:2000]
    if ".." in blob and ("C:\\Windows" in blob or "/etc/" in blob or "System32" in blob):
        return False, "Out-of-workspace escape"
    return _ok()


def inv_rate_limit(s: Dict[str, Any]) -> Tuple[bool, str]:
    if int(s.get("tool_calls_count", 0) or 0) > 200:
        return False, "Tool-call budget exhausted"
    if int(s.get("tokens_consumed", 0) or 0) > 1_000_000:
        return False, "Token budget exhausted"
    return _ok()


def inv_checkpoint_freshness(s: Dict[str, Any]) -> Tuple[bool, str]:
    age = float(s.get("checkpoint_age_s", 0) or 0)
    if age > 3600:
        return False, f"Checkpoint stale ({age:.0f}s)"
    return _ok()


def inv_goal_invariants_hold(s: Dict[str, Any]) -> Tuple[bool, str]:
    viols = s.get("goal_violations") or []
    if viols:
        return False, f"Goal invariant violations: {viols[:2]}"
    return _ok()


def inv_authority_present(s: Dict[str, Any]) -> Tuple[bool, str]:
    if not s.get("principal"):
        return False, "Missing principal identity"
    return _ok()


def inv_secrets_not_logged(s: Dict[str, Any]) -> Tuple[bool, str]:
    blob = str(s.get("action_args", ""))[:4000]
    for sig in ("sk-ant-", "sk-openai", "AKIA", "xoxb-", "ghp_"):
        if sig in blob and s.get("is_log_path"):
            return False, "Secret would be logged"
    return _ok()


INVARIANTS: List[Tuple[str, Check]] = [
    ("no_destructive_without_approval", inv_no_destructive_without_approval),
    ("no_raw_system_destroy", inv_no_raw_system_destroy),
    ("no_exfiltration", inv_no_exfiltration),
    ("no_path_traversal_to_secrets", inv_no_path_traversal_to_secrets),
    ("no_remote_code_exec", inv_no_remote_code_exec),
    ("prompt_injection_screen", inv_prompt_injection_screen),
    ("no_self_replication", inv_no_self_replication),
    ("corrigibility", inv_corrigibility),
    ("taint_no_shell", inv_taint_no_shell),
    ("kill_switch", inv_kill_switch),
    ("human_approval_r6", inv_human_approval_r6),
    ("provenance_required", inv_provenance_required),
    ("retrieval_latency", inv_retrieval_latency),
    ("backup_before_mutation", inv_backup_before_mutation),
    ("no_test_tampering", inv_no_test_tampering),
    ("output_law", inv_output_law),
    ("scope_containment", inv_scope_containment),
    ("rate_limit", inv_rate_limit),
    ("checkpoint_freshness", inv_checkpoint_freshness),
    ("goal_invariants_hold", inv_goal_invariants_hold),
    ("authority_present", inv_authority_present),
    ("secrets_not_logged", inv_secrets_not_logged),
]


def verify_invariants(state: Dict[str, Any]) -> Dict[str, Any]:
    failures: List[Dict[str, str]] = []
    for name, fn in INVARIANTS:
        try:
            ok, reason = fn(state)
        except Exception as e:
            ok, reason = False, f"checker error: {e}"
        if not ok:
            failures.append({"invariant": name, "reason": reason})
    return {"passed": not failures, "failures": failures, "checked": len(INVARIANTS)}
