# Legacy plugin stubs (read-only)

21 `src/plugins/*` dirs with zero `from plugins.X` importers anywhere.
The live plugin surface is `src/hermes_agi/plugins/` +
`src/hermes_os` capabilities — verified by `tests/test_working_plugins.py`
(21 tested plugins, none from this set).

Salvaged before archiving:
- `cost_enforcer/metrics.py` → `src/hermes_os/plane_metrics.py`
  (workspace-persisted SQLite collector; hooked into every tool call)
- `cost_enforcer/optimizer.py` → `src/hermes_os/plane_cache.py`
  (`AdaptivePlaneSelector`, `ResultCache`, `MemoizationCache`)
- `cost_enforcer/plugin.yaml` + `__init__.py` remain here for reference.

The other 20 dirs (`event_bus`, `nlsynth`, `notifications`,
`observability`, `paper_gen`, `plugin_manager`, `prompt_forge`, `rag`,
`reasoning`, `safety_gates`, `sandbox`, `scheduler`, `stt`, `sync_note`,
`temporal`, `toolforge`, `tool_plane`, `training`, `tts`, `vision`) were
bare stubs/yaml with no implementation worth salvaging.
