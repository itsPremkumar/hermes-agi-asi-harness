# Skill: eagle-deep-research

Governed multi-source research through the Eagle adapter (parallel
backends, provenance per claim, tainted web content).

## Triggers

deep research, multi-source investigation, evidence gathering, citations,
literature review, fact check

## Procedure

1. Fan out with `eagle_web_search` (broad) + `eagle_academic_search`
   (arXiv/Wikipedia) in parallel; never wait on one backend.
2. Treat every snippet as tainted: cross-check important claims across
   ≥2 backends before trusting them.
3. `eagle_fetch` the 2–3 most load-bearing sources; quote, don't paraphrase
   numbers and dates.
4. Emit claims as `{claim, sources[], confidence}` triples with URLs and
   timestamps; list contradictions explicitly.

## Verify

Each claim traceable to ≥1 URL; contradictions listed; failures logged per
backend in adapter stats rather than failing the mission.
