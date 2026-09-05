#!/usr/bin/env python3
"""Advanced formal verification layer for the Hermes AGI/ASI harness.

Features:
  - Temporal logic property specification (LTL/CTL operators & formulas)
  - Runtime invariant monitoring with violation detection
  - Model checking for finite-state properties (CTL model checker)
  - Human approval gates at R4-R6 boundaries with async gates
  - Circuit breaker pattern for failure isolation

All code is pure-Python stdlib — no external solver dependencies required
for the lightweight in-process model checker.  Heavy-weight tools (z3, nuXmv)
can be plugged in via the hook points on `FiniteStateModel` / `ModelChecker`.
"""

from __future__ import annotations

import ast
import dataclasses
import enum
import hashlib
import logging
import time
import uuid
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union

logger = logging.getLogger("hermes.formal")

# ---------------------------------------------------------------------------
# 1. Temporal Logic — LTL & CTL Operators & Formulas
# ---------------------------------------------------------------------------


class TemporalOperator(enum.Enum):
    # LTL (linear-time)
    X = "X"       # next
    F = "F"       # eventually
    G = "G"       # globally
    U = "U"       # until
    R = "R"       # release
    W = "W"       # weak until
    M = "M"       # strong release

    # CTL (branching-time)
    AX = "AX"
    EX = "EX"
    AF = "AF"
    EF = "EF"
    AG = "AG"
    EG = "EG"
    AU = "AU"
    EU = "EU"

    # Propositional
    TRUE = "true"
    FALSE = "false"
    NOT = "!"
    AND = "&"
    OR = "|"
    IMPLIES = "->"
    IFF = "<->"


@dataclass(frozen=True)
class LTLFormula:
    """Linear-time temporal logic formula (recursive AST)."""

    op: TemporalOperator
    # For atomic propositions: `arg` holds the string name
    arg: Optional[str] = None
    children: tuple[LTLFormula, ...] = ()

    # -- construction helpers ------------------------------------------------

    @staticmethod
    def prop(name: str) -> LTLFormula:
        return LTLFormula(TemporalOperator.TRUE, arg=name)  # reused convention

    @staticmethod
    def atom(name: str) -> LTLFormula:
        return LTLFormula(TemporalOperator.TRUE, arg=name)

    @staticmethod
    def next(p: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.X, children=(p,))

    @staticmethod
    def eventually(p: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.F, children=(p,))

    @staticmethod
    def globally(p: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.G, children=(p,))

    @staticmethod
    def until(p: LTLFormula, q: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.U, children=(p, q))

    @staticmethod
    def release(p: LTLFormula, q: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.R, children=(p, q))

    @staticmethod
    def weak_until(p: LTLFormula, q: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.W, children=(p, q))

    @staticmethod
    def not_(p: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.NOT, children=(p,))

    @staticmethod
    def and_(p: LTLFormula, q: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.AND, children=(p, q))

    @staticmethod
    def or_(p: LTLFormula, q: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.OR, children=(p, q))

    @staticmethod
    def implies(p: LTLFormula, q: LTLFormula) -> LTLFormula:
        return LTLFormula(TemporalOperator.IMPLIES, children=(p, q))

    # -- evaluation -----------------------------------------------------------

    def evaluate(self, trace: Sequence[Mapping[str, bool]]) -> bool:
        """Evaluate the LTL formula over a finite trace (list of state valuations)."""
        return _ltl_eval(self, trace, 0)

    def __repr__(self) -> str:
        return f"LTLFormula({self.op.value!r}, arg={self.arg!r}, children={self.children})"

    def to_string(self) -> str:
        return _ltl_to_string(self)


# CTL formulas — same recursive shape, different operators
CTLFormula = LTLFormula  # alias; operators include AX/EX/AF/EF/AG/EG/AU/EU


def _ltl_eval(f: LTLFormula, trace: Sequence[Mapping[str, bool]], pos: int) -> bool:
    """Recursive LTL evaluation over a finite trace."""
    op = f.op

    if op == TemporalOperator.TRUE:
        # Atomic proposition lookup
        if f.arg is None:
            return True
        return trace[pos].get(f.arg, False) if pos < len(trace) else False

    if op == TemporalOperator.NOT:
        return not _ltl_eval(f.children[0], trace, pos)
    if op == TemporalOperator.AND:
        return _ltl_eval(f.children[0], trace, pos) and _ltl_eval(f.children[1], trace, pos)
    if op == TemporalOperator.OR:
        return _ltl_eval(f.children[0], trace, pos) or _ltl_eval(f.children[1], trace, pos)
    if op == TemporalOperator.IMPLIES:
        return (not _ltl_eval(f.children[0], trace, pos)) or _ltl_eval(f.children[1], trace, pos)

    if pos >= len(trace):
        # Past the end of trace: G is true (vacuously), F/U/R are false
        if op == TemporalOperator.G:
            return True
        return False

    if op == TemporalOperator.X:
        return _ltl_eval(f.children[0], trace, pos + 1)
    if op == TemporalOperator.F:
        return any(_ltl_eval(f.children[0], trace, p) for p in range(pos, len(trace)))
    if op == TemporalOperator.G:
        return all(_ltl_eval(f.children[0], trace, p) for p in range(pos, len(trace)))
    if op == TemporalOperator.U:
        p, q = f.children
        for p_idx in range(pos, len(trace)):
            if _ltl_eval(q, trace, p_idx):
                return True
            if not _ltl_eval(p, trace, p_idx):
                return False
        return False  # U never satisfied before trace ends
    if op == TemporalOperator.R:
        p, q = f.children
        for p_idx in range(pos, len(trace)):
            if not _ltl_eval(p, trace, p_idx) and not _ltl_eval(q, trace, p_idx):
                return False
        return True
    if op == TemporalOperator.W:
        # weak until: p U q  OR  G p
        p, q = f.children
        # Check U
        for p_idx in range(pos, len(trace)):
            if _ltl_eval(q, trace, p_idx):
                return True
            if not _ltl_eval(p, trace, p_idx):
                break
        # Check G p
        return all(_ltl_eval(p, trace, p_idx) for p_idx in range(pos, len(trace)))
    if op == TemporalOperator.M:
        # strong release: q R p  =  not (not q U not p)
        return _ltl_release_strong(f.children[0], f.children[1], trace, pos)

    return False  # unknown operator


def _ltl_release_strong(p: LTLFormula, q: LTLFormula, trace: Sequence[Mapping[str, bool]], pos: int) -> bool:
    """Strong release: p M q  ==  G(p or q) AND F(q)."""
    # G(p or q)
    for idx in range(pos, len(trace)):
        if not (_ltl_eval(p, trace, idx) or _ltl_eval(q, trace, idx)):
            return False
    # F(q)
    return any(_ltl_eval(q, trace, idx) for idx in range(pos, len(trace)))


def _ltl_to_string(f: LTLFormula) -> str:
    op = f.op
    if op == TemporalOperator.TRUE:
        return f.arg if f.arg else "true"
    if op == TemporalOperator.NOT:
        return f"!{_ltl_to_string(f.children[0])}"
    if op == TemporalOperator.AND:
        return f"({_ltl_to_string(f.children[0])} & {_ltl_to_string(f.children[1])})"
    if op == TemporalOperator.OR:
        return f"({_ltl_to_string(f.children[0])} | {_ltl_to_string(f.children[1])})"
    if op == TemporalOperator.IMPLIES:
        return f"({_ltl_to_string(f.children[0])} -> {_ltl_to_string(f.children[1])})"
    if op == TemporalOperator.X:
        return f"X({_ltl_to_string(f.children[0])})"
    if op == TemporalOperator.F:
        return f"F({_ltl_to_string(f.children[0])})"
    if op == TemporalOperator.G:
        return f"G({_ltl_to_string(f.children[0])})"
    if op == TemporalOperator.U:
        return f"({_ltl_to_string(f.children[0])} U {_ltl_to_string(f.children[1])})"
    if op == TemporalOperator.R:
        return f"({_ltl_to_string(f.children[0])} R {_ltl_to_string(f.children[1])})"
    if op == TemporalOperator.W:
        return f"({_ltl_to_string(f.children[0])} W {_ltl_to_string(f.children[1])})"
    if op == TemporalOperator.M:
        return f"({_ltl_to_string(f.children[0])} M {_ltl_to_string(f.children[1])})"
    return op.value


def parse_ltl(spec: str) -> LTLFormula:
    """Parse a simple LTL formula string into an AST.

    Supported tokens:
      - atomic propositions: identifiers  (e.g. x, ready, lock_held)
      - operators: X, F, G, U, R, W, M, !, &, |, ->
      - parentheses for grouping

    This is a *subset* parser — sufficient for specification strings,
    not a full LTL grammar.  For production use, integrate a proper parser.
    """
    tokens = _tokenize_ltl(spec)
    ast_node, _ = _parse_ltl_parse(tokens, 0)
    return ast_node


def _tokenize_ltl(s: str) -> list[tuple[TemporalOperator, str]]:
    """Tokenize an LTL string into (operator, lexeme) pairs."""
    tokens: list[tuple[TemporalOperator, str]] = []
    i = 0
    op_map: dict[str, TemporalOperator] = {
        "X": TemporalOperator.X,
        "F": TemporalOperator.F,
        "G": TemporalOperator.G,
        "U": TemporalOperator.U,
        "R": TemporalOperator.R,
        "W": TemporalOperator.W,
        "M": TemporalOperator.M,
        "!": TemporalOperator.NOT,
        "&": TemporalOperator.AND,
        "|": TemporalOperator.OR,
    }
    while i < len(s):
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "(":
            tokens.append((TemporalOperator.TRUE, "("))  # placeholder
            i += 1
            continue
        if ch == ")":
            tokens.append((TemporalOperator.TRUE, ")"))
            i += 1
            continue
        if ch == "-" and i + 1 < len(s) and s[i + 1] == ">":
            tokens.append((TemporalOperator.IMPLIES, "->"))
            i += 2
            continue
        # multi-char operators: check longest first
        matched = False
        for length in (2, 1):
            if i + length <= len(s):
                substr = s[i : i + length]
                if substr in op_map:
                    tokens.append((op_map[substr], substr))
                    i += length
                    matched = True
                    break
        if matched:
            continue
        # identifier / keyword
        start = i
        while i < len(s) and (s[i].isalnum() or s[i] == "_"):
            i += 1
        ident = s[start:i]
        if not ident:
            raise ValueError(f"Unexpected character {ch!r} at position {i} in LTL spec")
        tokens.append((TemporalOperator.TRUE, ident))
    return tokens


def _parse_ltl_parse(tokens: list[tuple[TemporalOperator, str]], pos: int) -> tuple[LTLFormula, int]:
    """Simple recursive-descent parser for the LTL subset."""
    return _parse_implies(tokens, pos)


def _parse_implies(tokens, pos):
    left, pos = _parse_or(tokens, pos)
    while pos < len(tokens) and tokens[pos][0] == TemporalOperator.IMPLIES:
        pos += 1  # skip ->
        right, pos = _parse_or(tokens, pos)
        left = LTLFormula(TemporalOperator.IMPLIES, children=(left, right))
    return left, pos


def _parse_or(tokens, pos):
    left, pos = _parse_and(tokens, pos)
    while pos < len(tokens) and tokens[pos][0] == TemporalOperator.OR:
        pos += 1
        right, pos = _parse_and(tokens, pos)
        left = LTLFormula(TemporalOperator.OR, children=(left, right))
    return left, pos


def _parse_and(tokens, pos):
    left, pos = _parse_unary(tokens, pos)
    while pos < len(tokens) and tokens[pos][0] == TemporalOperator.AND:
        pos += 1
        right, pos = _parse_unary(tokens, pos)
        left = LTLFormula(TemporalOperator.AND, children=(left, right))
    return left, pos


def _parse_unary(tokens, pos):
    if pos >= len(tokens):
        raise ValueError("Unexpected end of LTL spec")
    op, lex = tokens[pos]
    if op == TemporalOperator.NOT:
        pos += 1
        child, pos = _parse_unary(tokens, pos)
        return LTLFormula(TemporalOperator.NOT, children=(child,)), pos
    if op in (TemporalOperator.X, TemporalOperator.F, TemporalOperator.G):
        pos += 1
        child, pos = _parse_unary(tokens, pos)
        return LTLFormula(op, children=(child,)), pos
    if op == TemporalOperator.TRUE and lex == "(":
        pos += 1
        inner, pos = _parse_implies(tokens, pos)
        if pos >= len(tokens) or tokens[pos][1] != ")":
            raise ValueError("Missing closing parenthesis in LTL spec")
        pos += 1
        return inner, pos
    # atomic proposition
    if op == TemporalOperator.TRUE:
        return LTLFormula.atom(lex), pos + 1
    raise ValueError(f"Unexpected token {lex!r} in LTL spec at position {pos}")


# ---------------------------------------------------------------------------
# 2. Runtime Invariant Monitor
# ---------------------------------------------------------------------------


@dataclass
class Invariant:
    """A runtime-checkable invariant."""

    name: str
    # Callable receiving current state dict -> bool
    predicate: Callable[[Mapping[str, Any]], bool]
    severity: str = "error"  # "error" | "warning"
    description: str = ""
    violation_count: int = field(default=0, repr=False)

    def check(self, state: Mapping[str, Any]) -> bool:
        try:
            result = bool(self.predicate(state))
        except Exception as exc:
            logger.warning(f"Invariant {self.name!r} raised exception: {exc}")
            result = False
        if not result:
            self.violation_count += 1
        return result


class RuntimeMonitor:
    """Monitors a stream of states against registered invariants.

    Usage
    -----
    >>> monitor = RuntimeMonitor()
    >>> monitor.add_invariant(Invariant("lock_free", lambda s: not s.get("locked")))
    >>> monitor.check_state({"locked": False, "count": 5})
    True
    >>> monitor.check_state({"locked": True})  # violation
    False
    """

    def __init__(self) -> None:
        self._invariants: dict[str, Invariant] = {}
        self._history: list[dict[str, Any]] = []
        self._violations: list[dict[str, Any]] = []
        self._listeners: list[Callable[[str, Mapping[str, Any]], None]] = []

    # -- lifecycle -----------------------------------------------------------

    def add_invariant(self, inv: Invariant) -> None:
        self._invariants[inv.name] = inv

    def remove_invariant(self, name: str) -> None:
        self._invariants.pop(name, None)

    def add_listener(self, callback: Callable[[str, Mapping[str, Any]], None]) -> None:
        self._listeners.append(callback)

    # -- checking ------------------------------------------------------------

    def check_state(self, state: Mapping[str, Any]) -> bool:
        """Check all invariants against *state*.  Returns True iff all pass."""
        self._history.append(dict(state))
        all_ok = True
        for inv in self._invariants.values():
            if not inv.check(state):
                all_ok = False
                entry = {
                    "invariant": inv.name,
                    "state": dict(state),
                    "time": time.time(),
                    "severity": inv.severity,
                }
                self._violations.append(entry)
                logger.warning(f"Invariant violation: {inv.name}: {inv.description or ''}")
                for listener in self._listeners:
                    try:
                        listener(inv.name, state)
                    except Exception as exc:
                        logger.error(f"Listener for {inv.name} raised: {exc}")
        return all_ok

    def check_ltl(self, formula: LTLFormula, trace: Sequence[Mapping[str, bool]]) -> bool:
        """Check an LTL property over a completed trace."""
        return formula.evaluate(trace)

    # -- queries -------------------------------------------------------------

    @property
    def violations(self) -> list[dict[str, Any]]:
        return list(self._violations)

    @property
    def invariant_status(self) -> dict[str, int]:
        return {name: inv.violation_count for name, inv in self._invariants.items()}

    def reset_violations(self) -> None:
        for inv in self._invariants.values():
            inv.violation_count = 0
        self._violations.clear()


# ---------------------------------------------------------------------------
# 3. Finite-State Model & CTL Model Checker
# ---------------------------------------------------------------------------


@dataclass
class Transition:
    """Edge in a Kripke structure."""

    source: str
    target: str
    label: Optional[str] = None  # action label


class FiniteStateModel:
    """A finite Kripke structure for model checking.

    Attributes
    ----------
    states : set[str]
        State names.
    init : str
        Initial state.
    transitions : list[Transition]
        Directed edges.
    labels : dict[str, set[str]]
        State -> set of atomic proposition names true in that state.
    """

    def __init__(self, init: str) -> None:
        self.states: set[str] = {init}
        self.init = init
        self.transitions: list[Transition] = []
        self.labels: dict[str, set[str]] = {init: set()}

    # -- construction --------------------------------------------------------

    def add_state(self, name: str, labels: Iterable[str] | None = None) -> None:
        self.states.add(name)
        if labels is not None:
            self.labels[name] = set(labels)
        if name not in self.labels:
            self.labels[name] = set()

    def add_transition(self, source: str, target: str, label: str | None = None) -> None:
        if source not in self.states:
            self.add_state(source)
        if target not in self.states:
            self.add_state(target)
        self.transitions.append(Transition(source, target, label))

    def set_labels(self, state: str, labels: Iterable[str]) -> None:
        self.labels[state] = set(labels)

    # -- queries -------------------------------------------------------------

    def successors(self, state: str) -> list[str]:
        return [t.target for t in self.transitions if t.source == state]

    def predecessors(self, state: str) -> list[str]:
        return [t.source for t in self.transitions if t.target == state]

    def ap_true(self, state: str, ap: str) -> bool:
        return ap in self.labels.get(state, set())


class ModelChecker:
    """CTL model checker on a FiniteStateModel.

    Implements the standard fixpoint algorithms for CTL* subset.
    Supports: AX, EX, AF, EF, AG, EG, AU, EU.
    """

    def __init__(self, model: FiniteStateModel) -> None:
        self.model = model
        self._cache: dict[str, set[str]] = {}

    # -- public API ----------------------------------------------------------

    def check(self, formula: CTLFormula, state: str | None = None) -> bool:
        """Check a CTL formula.  *state* defaults to the model's initial state."""
        state = state or self.model.init
        sat = self._check_ctl(formula, state)
        logger.info(f"CTL check: {formula.to_string()} @ {state} = {sat}")
        return sat

    def check_every_state(self, formula: CTLFormula) -> dict[str, bool]:
        """Check formula in every reachable state.  Returns state->bool mapping."""
        return {s: self._check_ctl(formula, s) for s in self.model.states}

    # -- CTL fixpoint algorithms ---------------------------------------------

    def _check_ctl(self, f: CTLFormula, state: str) -> bool:
        op = f.op

        if op == TemporalOperator.TRUE:
            return self.model.ap_true(state, f.arg) if f.arg else True
        if op == TemporalOperator.NOT:
            return not self._check_ctl(f.children[0], state)
        if op == TemporalOperator.AND:
            return self._check_ctl(f.children[0], state) and self._check_ctl(f.children[1], state)
        if op == TemporalOperator.OR:
            return self._check_ctl(f.children[0], state) or self._check_ctl(f.children[1], state)
        if op == TemporalOperator.IMPLIES:
            return (not self._check_ctl(f.children[0], state)) or self._check_ctl(f.children[1], state)

        # CTL path quantifiers
        if op == TemporalOperator.AX:
            return all(
                self._check_ctl(f.children[0], s) for s in self.model.successors(state)
            ) if self.model.successors(state) else True  # vacuous
        if op == TemporalOperator.EX:
            return any(
                self._check_ctl(f.children[0], s) for s in self.model.successors(state)
            )
        if op == TemporalOperator.AF:
            return self._check_af(f.children[0], state)
        if op == TemporalOperator.EF:
            return self._check_ef(f.children[0], state)
        if op == TemporalOperator.AG:
            return self._check_ag(f.children[0], state)
        if op == TemporalOperator.EG:
            return self._check_eg(f.children[0], state)
        if op == TemporalOperator.AU:
            return self._check_au(f.children[0], f.children[1], state)
        if op == TemporalOperator.EU:
            return self._check_eu(f.children[0], f.children[1], state)

        # LTL operators applied as branching-time with universal path
        if op == TemporalOperator.F:
            return self._check_af(f.children[0], state)  # AF ~= AF (all paths eventually)
        if op == TemporalOperator.G:
            return self._check_ag(f.children[0], state)
        if op == TemporalOperator.U:
            return self._check_au(f.children[0], f.children[1], state)

        logger.warning(f"Unhandled CTL operator {op}")
        return False

    # -- fixpoint computations -----------------------------------------------

    def _check_af(self, p: LTLFormula, state: str) -> bool:
        """AF p = νZ. p ∨ AX Z (greatest fixpoint)."""
        z = set()
        changed = True
        while changed:
            changed = False
            for s in self.model.states:
                if self._check_ctl(p, s):
                    if s not in z:
                        z.add(s)
                        changed = True
                else:
                    # All successors in Z?
                    succs = self.model.successors(s)
                    if succs and all(su in z for su in succs) and s not in z:
                        z.add(s)
                        changed = True
        return state in z

    def _check_eg(self, p: LTLFormula, state: str) -> bool:
        """EG p = μZ. p ∧ EX Z (least fixpoint)."""
        z = set()
        changed = True
        while changed:
            changed = False
            for s in self.model.states:
                if self._check_ctl(p, s):
                    succs = self.model.successors(s)
                    if succs and any(su in z or (su == s and p.op == TemporalOperator.TRUE and self._check_ctl(p, su)) for su in succs):
                        if s not in z:
                            z.add(s)
                            changed = True
                    elif not succs:  # deadlock — treat as existential path of length 0
                        if s not in z and self._check_ctl(p, s):
                            z.add(s)
                            changed = True
        # Iterate properly: EG p = least fixpoint of Y = p ∧ EX Y
        z = set()
        changed = True
        while changed:
            changed = False
            for s in self.model.states:
                if s in z:
                    continue
                if not self._check_ctl(p, s):
                    continue
                succs = self.model.successors(s)
                if succs and any(su in z for su in succs):
                    z.add(s)
                    changed = True
                elif not succs:  # deadlock — EG holds vacuously after one step? Standard semantics: deadlock = path of length 0, so EG p holds if p holds at deadlock
                    z.add(s)
                    changed = True
        return state in z

    def _check_ef(self, p: LTLFormula, state: str) -> bool:
        """EF p = μZ. p ∨ EX Z (least fixpoint)."""
        z = set()
        changed = True
        while changed:
            changed = False
            for s in list(self.model.states):
                if s in z:
                    continue
                if self._check_ctl(p, s):
                    z.add(s)
                    changed = True
                else:
                    preds = self.model.predecessors(s)
                    if any(pr in z for pr in preds):
                        z.add(s)
                        changed = True
        return state in z

    def _check_ag(self, p: LTLFormula, state: str) -> bool:
        """AG p = νZ. p ∧ AX Z (greatest fixpoint)."""
        z = set(self.model.states)  # start with all states
        changed = True
        while changed:
            changed = False
            for s in list(z):
                if not self._check_ctl(p, s):
                    z.discard(s)
                    changed = True
                else:
                    succs = self.model.successors(s)
                    if succs and not all(su in z for su in succs):
                        z.discard(s)
                        changed = True
        return state in z

    def _check_au(self, p: LTLFormula, q: LTLFormula, state: str) -> bool:
        """AU p q = νZ. q ∨ (p ∧ AX Z)."""
        z = set(self.model.states)
        changed = True
        while changed:
            changed = False
            for s in list(z):
                if self._check_ctl(q, s):
                    continue
                if not self._check_ctl(p, s):
                    z.discard(s)
                    changed = True
                else:
                    succs = self.model.successors(s)
                    if succs and all(su in z for su in succs):
                        continue
                    else:
                        z.discard(s)
                        changed = True
        return state in z

    def _check_eu(self, p: LTLFormula, q: LTLFormula, state: str) -> bool:
        """EU p q = μZ. q ∨ (p ∧ EX Z)."""
        z = set()
        changed = True
        while changed:
            changed = False
            for s in self.model.states:
                if s in z:
                    continue
                if self._check_ctl(q, s):
                    z.add(s)
                    changed = True
                elif self._check_ctl(p, s):
                    succs = self.model.successors(s)
                    if any(su in z for su in succs):
                        z.add(s)
                        changed = True
        return state in z


# ---------------------------------------------------------------------------
# 4. Human Approval Gates
# ---------------------------------------------------------------------------


class GateStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    TIMED_OUT = "timed_out"


@dataclass
class ApprovalGate:
    """Human-in-the-loop approval gate at a critical boundary.

    Parameters
    ----------
    gate_id : str
        Unique identifier.
    description : str
        Human-readable description of what needs approval.
    context : dict
        Arbitrary context snapshot (state, proposal, diff, etc.).
    timeout_sec : float
        Max seconds to wait for human decision before auto-escalation.
    required_approvers : int
        Minimum number of distinct approvals required.
    auto_escalate : bool
        Whether to auto-escalate on timeout.
    """

    gate_id: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    timeout_sec: float = 300.0
    required_approvers: int = 1
    auto_escalate: bool = True
    created_at: float = field(default_factory=time.time)

    # mutable state
    _status: GateStatus = field(default=GateStatus.PENDING, repr=False)
    _approvals: set[str] = field(default_factory=set, repr=False)  # approver IDs
    _rejected: bool = field(default=False, repr=False)
    _decision_time: float | None = field(default=None, repr=False)
    _decided_by: str | None = field(default=None, repr=False)

    @property
    def status(self) -> GateStatus:
        if self._status == GateStatus.PENDING and self._decision_time is not None:
            return self._status  # already set
        # timeout check
        if self._status == GateStatus.PENDING and (time.time() - self.created_at) > self.timeout_sec:
            if self.auto_escalate:
                self._status = GateStatus.TIMED_OUT
            else:
                self._status = GateStatus.ESCALATED
        return self._status

    @property
    def is_approved(self) -> bool:
        return self.status == GateStatus.APPROVED

    @property
    def is_blocked(self) -> bool:
        s = self.status
        return s in (GateStatus.PENDING, GateStatus.TIMED_OUT, GateStatus.ESCALATED)

    def approve(self, approver_id: str) -> bool:
        """Record an approval.  Returns True if gate now satisfied."""
        if self._status in (GateStatus.APPROVED, GateStatus.REJECTED):
            return self._status == GateStatus.APPROVED
        self._approvals.add(approver_id)
        if len(self._approvals) >= self.required_approvers:
            self._status = GateStatus.APPROVED
            self._decision_time = time.time()
            return True
        return False

    def reject(self, approver_id: str) -> None:
        self._rejected = True
        self._status = GateStatus.REJECTED
        self._decision_time = time.time()
        self._decided_by = approver_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "description": self.description,
            "status": self.status.value,
            "approvals": list(self._approvals),
            "required": self.required_approvers,
            "timeout_sec": self.timeout_sec,
            "created_at": self.created_at,
            "decision_time": self._decision_time,
            "context": self.context,
        }


# ---------------------------------------------------------------------------
# 5. Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Failure-isolation circuit breaker.

    After *failure_threshold* consecutive failures, the breaker opens and
    blocks calls for *recovery_timeout_sec*.  After that window, a single
    probe call is allowed (half-open); success closes the breaker again.

    Parameters
    ----------
    failure_threshold : int
        Consecutive failures before opening.
    recovery_timeout_sec : float
        Seconds to wait before attempting recovery.
    half_open_max_calls : int
        Max probe calls allowed in half-open state.
    on_open : Callable | None
        Callback invoked when the breaker transitions to OPEN.
    on_close : Callable | None
        Callback invoked when the breaker transitions to CLOSED.
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout_sec: float = 60.0
    half_open_max_calls: int = 1
    on_open: Callable[[], None] | None = None
    on_close: Callable[[], None] | None = None

    # mutable state
    _state: CircuitBreakerState = field(default=CircuitBreakerState.CLOSED, repr=False)
    _failure_count: int = field(default=0, repr=False)
    _success_count: int = field(default=0, repr=False)
    _opened_at: float | None = field(default=None, repr=False)
    _half_open_calls: int = field(default=0, repr=False)
    _total_failures: int = field(default=0, repr=False, metadata={"description": "cumulative"})
    _total_successes: int = field(default=0, repr=False, metadata={"description": "cumulative"})

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN and self._opened_at is not None:
            if (time.time() - self._opened_at) >= self.recovery_timeout_sec:
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    @property
    def is_open(self) -> bool:
        return self.state == CircuitBreakerState.OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute *func* through the circuit breaker.

        Raises
        ------
        CircuitBreakerOpen
            If the breaker is open and not in half-open recovery.
        """
        if self.is_open:
            raise CircuitBreakerOpen(
                f"Circuit breaker {self.name!r} is OPEN; call blocked"
            )

        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as exc:
            self._record_failure()
            raise

    async def acall(self, afunc, *args, **kwargs) -> Any:
        """Async variant of `call`."""
        if self.is_open:
            raise CircuitBreakerOpen(
                f"Circuit breaker {self.name!r} is OPEN; call blocked"
            )
        try:
            result = await afunc(*args, **kwargs)
            self._record_success()
            return result
        except Exception as exc:
            self._record_failure()
            raise

    def _record_success(self) -> None:
        self._total_successes += 1
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._transition_to(CircuitBreakerState.CLOSED)
        else:
            self._failure_count = 0  # reset consecutive counter

    def _record_failure(self) -> None:
        self._total_failures += 1
        self._failure_count += 1
        if self._failure_count >= self.failure_threshold and self._state != CircuitBreakerState.OPEN:
            self._transition_to(CircuitBreakerState.OPEN)

    def _transition_to(self, new_state: CircuitBreakerState) -> None:
        old = self._state
        self._state = new_state
        logger.info(f"CircuitBreaker {self.name!r}: {old.value} -> {new_state.value}")
        if new_state == CircuitBreakerState.OPEN:
            self._opened_at = time.time()
            if self.on_open:
                try:
                    self.on_open()
                except Exception as exc:
                    logger.error(f"on_open callback raised: {exc}")
        elif new_state == CircuitBreakerState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            if self.on_close:
                try:
                    self.on_close()
                except Exception as exc:
                    logger.error(f"on_close callback raised: {exc}")

    def reset(self) -> None:
        """Force-closed the breaker and clear counters."""
        self._transition_to(CircuitBreakerState.CLOSED)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "consecutive_failures": self._failure_count,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
            "opened_at": self._opened_at,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_sec": self.recovery_timeout_sec,
        }


class CircuitBreakerOpen(Exception):
    """Raised when a call is blocked by an open circuit breaker."""


# ---------------------------------------------------------------------------
# 6. Orchestration Layer
# ---------------------------------------------------------------------------


@dataclass
class VerificationRule:
    """A single verification rule combining temporal specification + invariant."""

    rule_id: str
    name: str
    ltl_formula: Optional[LTLFormula] = None
    invariant: Optional[Invariant] = None
    ctl_formula: Optional[CTLFormula] = None
    model: Optional[FiniteStateModel] = None
    gate: Optional[ApprovalGate] = None
    circuit_breaker: Optional[CircuitBreaker] = None


class FormalVerificationLayer:
    """Top-level orchestrator for the formal verification layer.

    Coordinates runtime monitoring, model checking, temporal property
    checking, and human approval gates.

    Examples
    --------
    >>> fvl = FormalVerificationLayer()
    >>> fvl.add_invariant("count_pos", lambda s: s.get("count", 0) >= 0)
    >>> fvl.check_state({"count": 5})
    True
    >>> fvl.check_state({"count": -1})  # violation
    False
    """

    def __init__(self) -> None:
        self._monitor = RuntimeMonitor()
        self._gates: dict[str, ApprovalGate] = {}
        self._breakers: dict[str, CircuitBreaker] = {}
        self._rules: dict[str, VerificationRule] = {}
        self._trace: list[dict[str, Any]] = []
        self._check_points: list[dict[str, Any]] = []

    # --- Invariants / Runtime Monitoring ------------------------------------

    def add_invariant(self, name: str, predicate: Callable[[Mapping[str, Any]], bool], **kw) -> None:
        self._monitor.add_invariant(Invariant(name=name, predicate=predicate, **kw))

    def remove_invariant(self, name: str) -> None:
        self._monitor.remove_invariant(name)

    def check_state(self, state: Mapping[str, Any]) -> bool:
        ok = self._monitor.check_state(state)
        self._trace.append({"time": time.time(), "state": dict(state), "ok": ok})
        return ok

    @property
    def violations(self) -> list[dict[str, Any]]:
        return self._monitor.violations

    @property
    def invariant_status(self) -> dict[str, int]:
        return self._monitor.invariant_status

    # --- Temporal Properties ------------------------------------------------

    def check_ltl(self, formula: LTLFormula, trace: Sequence[Mapping[str, bool]] | None = None) -> bool:
        """Check an LTL formula over the accumulated trace or a provided one."""
        t = trace if trace is not None else self._trace
        return formula.evaluate(t)

    def ltl_always(self, prop_name: str) -> LTLFormula:
        return LTLFormula.globally(LTLFormula.atom(prop_name))

    def ltl_eventually(self, prop_name: str) -> LTLFormula:
        return LTLFormula.eventually(LTLFormula.atom(prop_name))

    def ltl_next(self, prop_name: str) -> LTLFormula:
        return LTLFormula.next(LTLFormula.atom(prop_name))

    def ltl_until(self, p_name: str, q_name: str) -> LTLFormula:
        return LTLFormula.until(LTLFormula.atom(p_name), LTLFormula.atom(q_name))

    # --- CTL / Model Checking -----------------------------------------------

    def build_model(self, init: str = "s0") -> FiniteStateModel:
        model = FiniteStateModel(init)
        return model

    def check_ctl(self, formula: CTLFormula, model: FiniteStateModel | None = None, state: str | None = None) -> bool:
        m = model or self._default_model()
        checker = ModelChecker(m)
        return checker.check(formula, state)

    def _default_model(self) -> FiniteStateModel:
        m = FiniteStateModel("s0")
        m.add_state("s0", ["init"])
        m.add_state("s1", ["running"])
        m.add_transition("s0", "s1")
        return m

    # --- Approval Gates -----------------------------------------------------

    def create_gate(
        self,
        gate_id: str | None = None,
        description: str = "",
        timeout_sec: float = 300.0,
        required_approvers: int = 1,
        context: dict[str, Any] | None = None,
    ) -> ApprovalGate:
        gid = gate_id or f"gate-{uuid.uuid4().hex[:8]}"
        gate = ApprovalGate(
            gate_id=gid,
            description=description,
            context=context or {},
            timeout_sec=timeout_sec,
            required_approvers=required_approvers,
        )
        self._gates[gid] = gate
        return gate

    def get_gate(self, gate_id: str) -> ApprovalGate | None:
        return self._gates.get(gate_id)

    def approve_gate(self, gate_id: str, approver_id: str = "human") -> bool:
        gate = self._gates.get(gate_id)
        if gate is None:
            raise KeyError(f"Gate {gate_id!r} not found")
        return gate.approve(approver_id)

    def reject_gate(self, gate_id: str, approver_id: str = "human") -> None:
        gate = self._gates.get(gate_id)
        if gate is None:
            raise KeyError(f"Gate {gate_id!r} not found")
        gate.reject(approver_id)

    @property
    def pending_gates(self) -> list[ApprovalGate]:
        return [g for g in self._gates.values() if g.is_blocked]

    # --- Circuit Breakers ---------------------------------------------------

    def add_circuit_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_sec: float = 60.0,
        on_open: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> CircuitBreaker:
        cb = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout_sec=recovery_timeout_sec,
            on_open=on_open,
            on_close=on_close,
        )
        self._breakers[name] = cb
        return cb

    def get_circuit_breaker(self, name: str) -> CircuitBreaker | None:
        return self._breakers.get(name)

    def call_through_breaker(self, name: str, func: Callable, *args, **kwargs) -> Any:
        cb = self._breakers.get(name)
        if cb is None:
            raise KeyError(f"Circuit breaker {name!r} not found")
        return cb.call(func, *args, **kwargs)

    # --- Rules --------------------------------------------------------------

    def add_rule(self, rule: VerificationRule) -> None:
        self._rules[rule.rule_id] = rule

    def check_rule(self, rule_id: str) -> dict[str, Any]:
        rule = self._rules.get(rule_id)
        if rule is None:
            raise KeyError(f"Rule {rule_id!r} not found")
        result: dict[str, Any] = {"rule_id": rule_id, "name": rule.name}

        # Check invariant
        if rule.invariant:
            result["invariant_ok"] = rule.invariant.check(self._trace[-1]["state"]) if self._trace else False

        # Check LTL over trace
        if rule.ltl_formula:
            result["ltl_ok"] = rule.ltl_formula.evaluate(self._trace)

        # Check CTL on model
        if rule.ctl_formula and rule.model:
            checker = ModelChecker(rule.model)
            result["ctl_ok"] = checker.check(rule.ctl_formula)

        # Gate check
        if rule.gate:
            result["gate_status"] = rule.gate.status.value
            result["gate_blocked"] = rule.gate.is_blocked

        # Circuit breaker check
        if rule.circuit_breaker:
            result["breaker_state"] = rule.circuit_breaker.state.value

        self._check_points.append(result)
        return result

    # --- Exported state -----------------------------------------------------

    @property
    def trace(self) -> list[dict[str, Any]]:
        return list(self._trace)

    @property
    def check_points(self) -> list[dict[str, Any]]:
        return list(self._check_points)

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariants": self._monitor.invariant_status,
            "violations": self._monitor.violations,
            "gates": {gid: g.to_dict() for gid, g in self._gates.items()},
            "breakers": {name: b.stats for name, b in self._breakers.items()},
            "trace_length": len(self._trace),
            "check_points": len(self._check_points),
        }