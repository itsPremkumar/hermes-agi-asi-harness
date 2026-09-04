# Legacy CLI archive (read-only)

Superseded standalone entry points, kept for history. Do not import from
active code; the supported surface is `python -m hermes_agi` (`src/hermes_agi/`).

| File | Superseded by |
|---|---|
| `hermes_v8.py`, `hermes_v9.py`, `hermes_ultimate.py` | `python -m hermes_agi run` + `HermesIntelligenceOS` |
| `hermes_engine.py`, `hermes_supervisor.py`, `harness_control_plane.py` | `src/hermes_os/kernel.py`, `supervisor.py`, `daemon.py` |
| `hermes_integration.py` | `src/hermes_os/hermes_controller.py` |
| `master.py` | `python -m hermes_agi daemon run` |
| `smoke_test.py`, `run_verification.py` | `pytest tests/` |
| `install.py`, `install_for_hermes.py`, `setup_package.py` | `pip install -e .` |
| `safety_plugin.py`, `capability_registry.py` | `src/hermes_os/safety_kernel.py`, `capabilities.py` |

Kept at root (not archived): `continuous_dev.py` — still imported by
`tests/test_continuous_dev.py`; `hermes.py` — still referenced by runtime docs
(both migrate in a follow-up).
