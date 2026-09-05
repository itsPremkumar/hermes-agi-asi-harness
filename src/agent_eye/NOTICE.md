# NOTICE — src/agent_eye provenance

This subtree is a vendored web-research toolkit ("AgentEye" / Agent Search
Lite style backends). Only the research capacity is used, exclusively
through `src/hermes_os/eagle_adapter.py` (parallel fan-out, timeouts,
provenance, taint) — nothing else in the harness imports it.

## License status: UNRESOLVED

* No LICENSE/COPYING file ships with this subtree.
* The sibling `src/plugins/agent_eye_search/` header claims
  "Extracted & enhanced from AgentEye by itsPremkumar (MIT License)".
* The harness root LICENSE is MIT (Prem Kumar).

## Required before any wheel release containing this subtree

1. Confirm the upstream origin and its license (ideally add the upstream
   LICENSE file here verbatim).
2. If the upstream license is not MIT-compatible, either replace the
   backends used by `eagle_adapter` (wikipedia/github/arXiv wrappers) with
   clean-room implementations or move this subtree to an optional extra.

Until then: do not expand usage beyond `eagle_adapter.py`.
