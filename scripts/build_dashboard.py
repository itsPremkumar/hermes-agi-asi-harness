#!/usr/bin/env python3
"""Zero-dependency dashboard: renders .hermes state into .hermes/dashboard.html.
Usage: python scripts/build_dashboard.py [--root .]
"""
import argparse
import html
import json
from pathlib import Path


def read_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def tail_jsonl(p, n=50):
    try:
        lines = Path(p).read_text(encoding="utf-8").splitlines()[-n:]
        return [json.loads(x) for x in lines if x.strip()]
    except Exception:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    h = root / ".hermes"

    queue = read_json(h / "daemon_queue.json", [])
    radar = read_json(h / "radar.json", {})
    eagle = read_json(h / "eagle_stats.json", {})
    eagle_health = read_json(h / "eagle_health.json", {})
    scores = read_json(h / "tool_scores.json", {})
    portfolio = read_json(h / "model_portfolio.json", {})
    events = tail_jsonl(h / "events" / "audit.jsonl", 30)
    ledger_lines = tail_jsonl(h / "memory" / "economic_ledger.jsonl", 200)
    tokens = sum(e.get("tokens", 0) for e in ledger_lines)
    cost = sum(e.get("cost_usd", 0.0) for e in ledger_lines)
    checkpoints = sorted((h / "checkpoints").glob("*.json")) if (h / "checkpoints").exists() else []
    forensics = sorted((h / "forensics").glob("*.json")) if (h / "forensics").exists() else []
    kill = (h / "KILL").exists()

    def row(k, v):
        return f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>"

    body = f"""
<h1>Hermes 24/7 Dashboard</h1>
<p>KILL switch: <b>{'ENGAGED' if kill else 'off'}</b> | queue: <b>{len(queue)}</b> |
checkpoints: <b>{len(checkpoints)}</b> | ledger: <b>{tokens} tokens / ${cost:.4f}</b> |
forensics: <b>{len(forensics)}</b></p>
<h2>Queue</h2><table>{''.join(row(q.get('mission_id'), q.get('request', '')[:100]) for q in queue) or '<tr><td>empty</td></tr>'}</table>
<h2>Eagle research</h2><table>{row('queries', eagle.get('queries', 0)) + row('elapsed_total', eagle.get('elapsed_total', 0)) + ''.join(row('backend ' + n, d.get('status', '?') + f" h={d.get('hits', 0)} f={d.get('fails', 0)}") for n, d in (eagle_health.get('backends', {}) or {}).items()) or '<tr><td>no data</td></tr>'}</table>
<h2>Model portfolio</h2><table>{''.join(row(m, f"{d.get('role')} sr={d.get('success_rate')} n={d.get('invocations')}") for m, d in portfolio.items()) or '<tr><td>—</td></tr>'}</table>
<h2>Tool scores</h2><table>{''.join(row(t, f"sr={d.get('success_rate')} n={d.get('n')}") for t, d in list(scores.items())[:20]) or '<tr><td>—</td></tr>'}</table>
<h2>Tech radar</h2><table>{''.join(row(n, f"{d.get('status')} ({d.get('score')})") for n, d in list(radar.items())[:30]) or '<tr><td>—</td></tr>'}</table>
<h2>Recent events</h2><table>{''.join(row(e.get('event_type'), e.get('payload', {}).get('mission_id', e.get('payload', {}).get('request', ''))) for e in events[-15:]) or '<tr><td>—</td></tr>'}</table>
<h2>Checkpoints</h2><table>{''.join(row(c.stem, '') for c in checkpoints[-15:]) or '<tr><td>—</td></tr>'}</table>
"""
    doc = ("<html><head><meta charset='utf-8'><title>Hermes Dashboard</title>"
           "<style>body{font-family:sans-serif;margin:2em}table{border-collapse:collapse}"
           "td{border:1px solid #ccc;padding:4px 8px}</style></head><body>" + body + "</body></html>")
    out = h / "dashboard.html"
    out.write_text(doc, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
