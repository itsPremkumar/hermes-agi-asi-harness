# Scripts index

## Daemon lifecycle (run in this order)

| Script | Purpose |
|---|---|
| `install_daemon_task.ps1` | Register `HermesAGI-Daemon` boot task (restart on failure) |
| `uninstall_daemon_task.ps1` | Remove the task |

## State & inspection

| Script | Purpose |
|---|---|
| `backup_state.ps1 backup\|restore\|list` | Zip/restore `.hermes/` continuity state |
| `build_dashboard.py [--root .]` | Render `.hermes/` state to `.hermes/dashboard.html` |

All scripts are Windows-first (PowerShell) except `build_dashboard.py`
(stdlib Python, cross-platform). Runtime state they touch is git-ignored.
