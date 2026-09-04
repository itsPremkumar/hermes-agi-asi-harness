"""Hermes-first LLM chain: order, fallback, and compiler default (offline-safe)."""
import os
import sys

sys.path.insert(0, "src")

from hermes_os import hermes_llm as HL


def _reset():
    HL._last_probe.update({"tier": None, "ts": 0.0})


def test_order_env_parsing(monkeypatch):
    monkeypatch.setenv("HERMES_LLM_ORDER", "L,C")
    assert HL._order() == ["L", "C"]
    monkeypatch.setenv("HERMES_LLM_ORDER", "bogus")
    assert HL._order() == ["H1", "H2", "L", "C"]


def test_falls_to_deterministic_when_all_down(monkeypatch):
    _reset()
    monkeypatch.setenv("HERMES_LLM_ORDER", "H1,H2,L")
    monkeypatch.setattr(HL, "PROBE_TIMEOUT", 0.5)
    resolved = HL.resolve_tier(force_refresh=True)
    assert resolved.get("tier") is None
    client = HL.HermesFirstLLMClient(timeout=5)
    assert client.chat([{"role": "user", "content": "hi"}]) is None
    assert client.generate("hi") is None


def test_h1_beats_cloud_when_up(monkeypatch):
    _reset()
    monkeypatch.setenv("HERMES_LLM_ORDER", "H1,H2,L,C")
    monkeypatch.setitem(HL._PROBERS, "H1", lambda: ("http://127.0.0.1:9/v1", "k", "m-h1"))
    monkeypatch.setattr(HL, "_chat_openai_compat",
                        lambda *a, **k: "hermes-answer" if a[2] == "m-h1" else None)
    client = HL.HermesFirstLLMClient(timeout=5)
    assert client.chat([{"role": "user", "content": "hi"}]) == "hermes-answer"
    assert client.active_tier == "H1"


def test_dead_h1_falls_through_to_next_tier(monkeypatch):
    _reset()
    calls = []

    def fake_resolve(force_refresh=False):
        # First call claims H1, after failure claims L
        tier = "L" if calls else "H1"
        calls.append(tier)
        return {"tier": tier, "base_url": f"http://x/{tier}", "api_key": "",
                "model": f"m-{tier}", "ts": 9999999999.0}

    monkeypatch.setattr(HL, "resolve_tier", fake_resolve)
    monkeypatch.setattr(HL, "_chat_openai_compat",
                        lambda base, key, model, *a, **k: "local-answer" if model == "m-L" else None)
    client = HL.HermesFirstLLMClient(timeout=5)
    assert client.chat([{"role": "user", "content": "hi"}]) == "local-answer"
    assert calls[0] == "H1" and "L" in calls


def test_compiler_defaults_to_hermes_first():
    from hermes_os.cognitive_compiler import CognitiveCompiler
    comp = CognitiveCompiler(workspace_root=".", enable_llm=True)
    assert type(comp.llm_client).__name__ == "HermesFirstLLMClient"
    comp_off = CognitiveCompiler(workspace_root=".", enable_llm=False)
    assert comp_off.llm_client is None


def test_portfolio_hides_hermes_when_down():
    _reset()
    from hermes_os.model_router import ModelPortfolio
    pf = ModelPortfolio(workspace_root=".")
    routed = pf.route("coding")
    assert not routed.model_id.startswith("hermes_")
