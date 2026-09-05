#!/usr/bin/env python3
"""Fail on import cycles between src top-level packages (hermes_os, memory, ...).

Usage: python scripts/check_cycles.py [--root .] [--allow file]
Intra-package imports are fine; only cross-package cycles fail the build.
An allowlist file (one `a -> b` per line) grandfathers known cases.
"""
import argparse
import re
import sys
from pathlib import Path

IMPORT_RE = re.compile(r"^\s*(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))", re.M)


def top(mod: str) -> str:
    return mod.split(".")[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--allow", default="")
    args = ap.parse_args()
    src = Path(args.root) / "src"
    allowed = set()
    if args.allow and Path(args.allow).exists():
        allowed = {l.strip() for l in Path(args.allow).read_text().splitlines() if "->" in l}

    edges: dict[str, set[str]] = {}
    for path in sorted(src.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            mod = path.relative_to(src).with_suffix("").as_posix().replace("/", ".")
        except Exception:
            continue
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        frm = top(mod)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        for m in IMPORT_RE.finditer(text):
            dep = ((m.group(1) or m.group(2)).split(",")[0].strip())
            dep = re.split(r"\s+as\s+", dep)[0].strip().lstrip(".")
            if not dep or dep == frm:
                continue
            to = top(dep)
            if to != frm:
                edges.setdefault(frm, set()).add(to)

    # Only consider edges between existing top packages
    pkgs = {p.name for p in src.iterdir() if p.is_dir() and (p / "__init__.py").exists()
            or p.suffix == ".py"}
    pkgs = {p.name if (src / p.name).is_dir() else p.stem
            for p in src.iterdir() if p.name != "__pycache__"}
    edges = {a: {b for b in bs if b in pkgs} for a, bs in edges.items()}

    # Tarjan SCC
    index, low, stack, on_stack, counter, sccs = {}, {}, [], set(), [0], []

    def strong(v):
        index[v] = low[v] = counter[0]
        counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in edges.get(v, ()):
            if w not in index:
                strong(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                sccs.append(sorted(comp))

    for v in sorted(pkgs):
        if v not in index:
            strong(v)

    bad = []
    for comp in sccs:
        key = " -> ".join(comp + [comp[0]])
        if key not in allowed:
            bad.append(key)
    if bad:
        print("IMPORT CYCLES:")
        for b in bad:
            print("  " + b)
        return 1
    print(f"no import cycles across {len(pkgs)} top packages")
    return 0


if __name__ == "__main__":
    sys.exit(main())
