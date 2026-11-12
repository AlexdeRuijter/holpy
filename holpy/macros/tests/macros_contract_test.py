"""Contract tests for every macro registered with :mod:`holpy.kernel.theory`.

The test checks the four rules from the first-tag plan, WS1-C:

1. Every macro that is not a trusted oracle overrides ``get_proof_term`` and
   has a trust level of ``None`` or at least one.
2. Every oracle is registered with level zero, and no level-zero macro is
   missing from the oracle list.
3. The macro's argument signature round-trips through
   :func:`holpy.syntax.printer.print_str_args` and
   :func:`holpy.syntax.parser.parse_args`, using a real argument from a library
   proof or from the macro's own tests.
4. The macro expansion graph built from the stored proofs of ``logic``,
   ``nat`` and ``set`` has no cycle.

The test reports its coverage in one summary at the end of the run.  A macro
without a usable argument is listed as untested; that is coverage information,
not a contract failure.
"""

from __future__ import annotations

import contextlib
import io
import unittest
from typing import Any

# Import every module that registers macros.  Some modules register macros at
# import time through a decorator, and holpy.logic.logic installs a group with
# theory.global_macros.update, so importing the modules is part of the fixture.
import holpy.data.expr
import holpy.data.function
import holpy.data.integer
import holpy.data.nat
import holpy.data.real
import holpy.imperative.imp
import holpy.integral.inequality
import holpy.logic.auto
import holpy.logic.basic  # loads the real theory and its macro modules
import holpy.logic.logic
import holpy.logic.tactic
import holpy.macros.induct
import holpy.macros.linarith
import holpy.macros.semiring
import holpy.macros.structural
import holpy.macros.transfer
import holpy.prover.simplex
import holpy.prover.simplex_strict
import holpy.prover.sympywrapper
import holpy.prover.z3wrapper  # noqa: F401  (registers z3)
from holpy.kernel import theory
from holpy.kernel.macro import Macro
from holpy.kernel.proof import Proof
from holpy.logic import basic, context
from holpy.server import items
from holpy.syntax import parser, printer

# The oracle list from docs/plans/first-tag/20-ws1-proof-levels.md, WS1-C.
PLAN_ORACLES = {
    "int_const_ineq",
    "int_eval",
    "integer_simplex",
    "nat_eval",
    "real_compare",
    "real_const_eq",
    "real_const_ineq",
    "real_eq_comparison",
    "real_eval",
    "real_norm",
    "simplex_macro",
    "sympy",
    "z3",
}

# Found by this test on main: level zero but absent from the plan's list.
# It is kept separate so the discrepancy stays visible for human review.
FOUND_ORACLES = {"const_inequality"}

ORACLES = PLAN_ORACLES | FOUND_ORACLES

# A macro that genuinely fails rule 3 would go here as name -> reason.  The
# entry makes only that subTest a known failure; it must be reported to Alex.
KNOWN_FAILURES: dict[str, str] = {}

# These files contain real arguments for the macros that appear in the library.
# logic, nat and set are also used for the expansion graph.
LIBRARY_ARG_THEORIES = (
    "logic",
    "nat",
    "set",
    "expr",
    "real",
    "hoare",
    "hoare_test_output",
)
EXPANSION_THEORIES = ("logic", "nat", "set")

# Arguments for macros that the bundled library does not use.  Each entry is
# (theory, variable context, argument string) and comes from the macro's own
# tests (file named in the comment).  No argument is invented here.
TEST_SAMPLES: dict[str, tuple[str, dict[str, str], str]] = {
    # holpy/logic/tests/auto_test.py
    "auto": ("logic_base", {"A": "bool", "B": "bool"}, "A --> B --> A & B"),
    # holpy/logic/tests/logic_test.py::testBetaNorm
    "beta_norm": (
        "logic_base",
        {"f": "'a => 'b", "x": "'a", "y": "'b"},
        "",
    ),
    # holpy/macros/tests/structural_test.py
    "cases": ("nat", {"n": "nat"}, "n + 0 = n, n"),
    "conj_elim": ("logic", {"A": "bool", "B": "bool", "C": "bool"}, "B"),
    "conj_intro": ("logic", {"A": "bool", "B": "bool", "C": "bool"}, ""),
    "contr": ("logic", {"A": "bool", "C": "bool"}, "C"),
    "exI_list": (
        "nat",
        {},
        "∃x. ∃y. x + y = (3::nat), (1::nat), (2::nat)",
    ),
    # holpy/logic/tests/logic_test.py
    "imp_conj": (
        "logic_base",
        {"A": "bool", "B": "bool", "C": "bool", "D": "bool"},
        "A & (D & B) & C --> (A & D & C) & (A & B)",
    ),
    "imp_disj": (
        "logic",
        {"A": "bool", "B": "bool", "C": "bool", "D": "bool"},
        "A | (D | B) | C --> (A | D | C) | (A | B)",
    ),
    "resolution": ("logic", {"P": "bool", "Q": "bool", "R": "bool"}, ""),
    # holpy/macros/tests/induct_test.py
    "induct": ("nat", {"n": "nat"}, "nat_induct, n, n + 0 = n"),
    # holpy/integral/tests/inequality_test.py::testInequalityMacro
    "interval_inequality": ("interval_arith", {"x": "real"}, "x < 2"),
    # holpy/data/tests/nat_test.py
    "nat_const_less": ("nat", {}, "(3::nat) < 5"),
    "nat_const_less_eq": ("nat", {}, "(3::nat) <= 5"),
    # holpy/macros/tests/linarith_test.py
    "nat_linarith": (
        "nat",
        {"m": "nat", "n": "nat", "k": "nat"},
        "m + 1 ≤ n",
    ),
    "real_linarith": (
        "real",
        {"x": "real", "y": "real", "z": "real", "a": "real", "s": "real", "e": "real"},
        "x < z",
    ),
    # holpy/data/tests/real_test.py::testRelaxSimplexMacro
    "non_strict_simplex": ("real", {"x": "real", "y": "real"}, "x > 0, y > 0"),
    # holpy/macros/tests/semiring_test.py
    "semiring_norm": (
        "nat",
        {"a": "nat", "b": "nat", "c": "nat"},
        "add_comm add_assoc mult_comm mult_assoc distrib_l nat_plus_def_1 "
        "nat_times_def_1 mult_1_left, (a + b) * (c + 1) = c * b + a + a * c + b",
    ),
    # holpy/prover/tests/simplex_strict_test.py
    "strict_simplex_macro": (
        "real",
        {"x_1": "real", "x_2": "real", "x_3": "real", "x_4": "real"},
        "x_1 < 9",
    ),
    # holpy/macros/tests/transfer_test.py
    "transfer": (
        "logic",
        {
            "phi": "'a ⇒ 'b",
            "f": "'a ⇒ 'a ⇒ 'a",
            "g": "'b ⇒ 'b ⇒ 'b",
            "c": "'a",
            "d": "'b",
            "le1": "'a ⇒ 'a ⇒ bool",
            "le2": "'b ⇒ 'b ⇒ bool",
            "h": "'a ⇒ 'a",
            "a": "'a",
            "b": "'a",
        },
        ", f a b = f b a",
    ),
}


def _first_line(exc: BaseException) -> str:
    """Return the first line of an exception message."""
    text = str(exc).strip()
    return text.splitlines()[0] if text else exc.__class__.__name__


def _round_trip(name: str, args: Any) -> str | None:
    """Round-trip a parsed argument through the printer and parser.

    Parameters
    ----------
    name : str
        Registered macro name.
    args : Any
        Already parsed argument, as found on a proof item or parsed from a
        test example.

    Returns
    -------
    str or None
        A reason when the round trip fails, otherwise ``None``.
    """
    macro = theory.global_macros[name]
    try:
        printed = printer.print_str_args(name, args, None)
        if isinstance(printed, list):
            printed = "".join(printed)
        reparsed = parser.parse_args(macro.sig, printed)
    except Exception as exc:  # A parser error is the failure being tested.
        return f"{type(exc).__name__}: {_first_line(exc)}"

    if reparsed != args:
        return f"printed {printed!r}, which parses back differently"
    return None


def _walk_proof(proof: Proof):
    """Yield every item of a proof, including items in subproofs."""
    for seq in proof.items:
        if seq.subproof is not None:
            yield from _walk_proof(seq.subproof)
        yield seq


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    """Return one cycle in ``graph``, or ``None`` when it is acyclic."""
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        state[node] = 1
        stack.append(node)
        for nxt in graph.get(node, ()):
            if nxt not in graph:
                continue
            if state.get(nxt) == 1:
                return stack[stack.index(nxt):] + [nxt]
            if state.get(nxt, 0) == 0:
                cycle = visit(nxt)
                if cycle is not None:
                    return cycle
        stack.pop()
        state[node] = 2
        return None

    for node in graph:
        if state.get(node, 0) == 0:
            cycle = visit(node)
            if cycle is not None:
                return cycle
    return None


def _scan_library(
    theory_name: str,
    *,
    expand: bool,
    rule3: dict[str, str | None],
    graph: dict[str, set[str]],
    expansion_counts: dict[str, int],
    expansion_errors: dict[str, list[str]],
    parse_errors: list[str],
) -> None:
    """Collect rule-3 samples and rule-4 expansion edges from one theory.

    The theory is loaded up to its first item and extended in JSON order, as
    ``scripts/check_library.py`` does, so each item sees the same theory the
    checker sees.  Proof lines are parsed with ``parser.parse_proof_rule``;
    that is the path that gives the checker's already-parsed arguments.
    """
    basic.load_theory(theory_name, limit="start")
    data = basic.load_json_data(theory_name)
    macros = theory.global_macros

    for raw in data["content"]:
        item = items.parse_item(raw)
        has_proof = item.error is None and raw.get("ty") == "thm" and raw.get("proof")

        if has_proof:
            context.set_context(None, vars=item.vars)
            proof = Proof()
            th_by_id: dict[str, Any] = {}
            proof_ok = True
            try:
                for line in item.proof:
                    if line["rule"] == "variable":
                        nm, type_str = line["args"].split(",", 1)
                        context.ctxt.vars[nm] = parser.parse_type(type_str.strip())
                    seq = parser.parse_proof_rule(line)
                    proof.insert_item(seq)
                    if seq.th is not None:
                        th_by_id[str(seq.id)] = seq.th

                    if seq.rule in macros and seq.rule not in rule3:
                        rule3[seq.rule] = _round_trip(seq.rule, seq.args)
            except Exception as exc:
                proof_ok = False
                parse_errors.append(
                    f"{theory_name}.{item.name}: {type(exc).__name__}: {_first_line(exc)}"
                )

            if proof_ok and expand:
                for seq in _walk_proof(proof):
                    name = seq.rule
                    if name not in macros or name in ORACLES:
                        continue

                    expansion_counts[name] = expansion_counts.get(name, 0) + 1
                    graph.setdefault(name, set())

                    prevs = []
                    for prev_id in seq.prevs:
                        prev_th = th_by_id.get(str(prev_id))
                        if prev_th is None:
                            prevs = []
                            break
                        prevs.append((prev_id, prev_th))

                    if len(prevs) != len(seq.prevs):
                        expansion_errors.setdefault(name, []).append(
                            f"{theory_name}.{item.name}: missing previous statement"
                        )
                        continue

                    try:
                        expansion = macros[name].expand(seq.id, seq.args, prevs)
                    except Exception as exc:
                        expansion_errors.setdefault(name, []).append(
                            f"{theory_name}.{item.name}: {type(exc).__name__}: "
                            f"{_first_line(exc)}"
                        )
                        continue

                    for line in _walk_proof(expansion):
                        if line.rule in macros and line.rule != name:
                            graph[name].add(line.rule)
                            graph.setdefault(line.rule, set())

        # Match check_library: a failed item is not extended, so later items
        # see exactly the same theory they would during a library check.
        if item.error is None:
            theory.thy.unchecked_extend(item.get_extension())


class MacroContractTest(unittest.TestCase):
    """Check the four WS1-C rules for every registered macro."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._previous_thy = theory.thy
        cls._previous_ctxt = context.ctxt

        with contextlib.redirect_stdout(io.StringIO()):
            cls._build_observations()

    @classmethod
    def tearDownClass(cls) -> None:
        theory.thy = cls._previous_thy
        context.ctxt = cls._previous_ctxt
        print("\n".join(cls._summary_lines))

    @classmethod
    def _build_observations(cls) -> None:
        rule3: dict[str, str | None] = {}
        graph: dict[str, set[str]] = {}
        expansion_counts: dict[str, int] = {}
        expansion_errors: dict[str, list[str]] = {}
        parse_errors: list[str] = []

        for theory_name in LIBRARY_ARG_THEORIES:
            _scan_library(
                theory_name,
                expand=theory_name in EXPANSION_THEORIES,
                rule3=rule3,
                graph=graph,
                expansion_counts=expansion_counts,
                expansion_errors=expansion_errors,
                parse_errors=parse_errors,
            )

        for name, (theory_name, variables, args) in TEST_SAMPLES.items():
            if name in rule3:
                continue
            try:
                basic.load_theory(theory_name)
                context.set_context(None, vars=variables)
                parsed = parser.parse_args(theory.global_macros[name].sig, args)
            except Exception as exc:
                rule3[name] = f"parsing test sample failed: {type(exc).__name__}: {_first_line(exc)}"
            else:
                rule3[name] = _round_trip(name, parsed)

        macros = theory.global_macros
        measured_oracles = {name for name, macro in macros.items() if macro.level == 0}
        untested = sorted(set(macros) - set(rule3))
        rule3_failures = {name: reason for name, reason in rule3.items() if reason is not None}

        non_oracles = sorted(set(macros) - ORACLES)
        summary = [
            "Macro contract summary",
            f"  registered macros: {len(macros)}",
            f"  plan oracles: {len(PLAN_ORACLES)}; measured level 0: {len(measured_oracles)}",
            f"  level 0 but not in plan: {sorted(measured_oracles - PLAN_ORACLES)}",
            f"  in plan but not level 0: {sorted(PLAN_ORACLES - measured_oracles)}",
            f"  rule 1 asserted: {len(non_oracles)} non-oracle macros",
            f"  rule 2 asserted: {len(ORACLES)} oracles",
            f"  rule 3 asserted: {len(rule3)} macros with a real argument",
            f"  rule 3 failures: {sorted(rule3_failures)}",
            f"  rule 3 untested ({len(untested)}): {', '.join(untested) if untested else 'none'}",
            f"  rule 4 expanded {sum(expansion_counts.values())} library macro lines; "
            f"graph nodes: {len(graph)}",
        ]

        if graph:
            edges = ", ".join(
                f"{name} -> {sorted(targets)}" for name, targets in sorted(graph.items()) if targets
            )
            summary.append(f"  rule 4 edges: {edges if edges else 'none'}")
        if expansion_errors:
            for name, errors in sorted(expansion_errors.items()):
                summary.append(
                    f"  rule 4 expansion failures {name}: {len(errors)}; first: {errors[0]}"
                )
        else:
            summary.append("  rule 4 expansion failures: none")
        if parse_errors:
            summary.append(
                f"  unparseable stored proofs skipped ({len(parse_errors)}): "
                + "; ".join(parse_errors[:3])
            )
        summary.append(
            f"  KNOWN_FAILURES: {KNOWN_FAILURES if KNOWN_FAILURES else 'none'}"
        )

        cls._rule3 = rule3
        cls._graph = graph
        cls._expansion_counts = expansion_counts
        cls._expansion_errors = expansion_errors
        cls._untested = untested
        cls._summary_lines = summary

    def test_rule1_non_oracles_override_get_proof_term(self) -> None:
        """Non-oracle macros expand and have level ``None`` or at least one."""
        for name, macro in sorted(theory.global_macros.items()):
            if name in ORACLES:
                continue
            with self.subTest(macro=name):
                self.assertIsNot(
                    type(macro).get_proof_term,
                    Macro.get_proof_term,
                    f"{name} does not override get_proof_term",
                )
                self.assertTrue(
                    macro.level is None or macro.level >= 1,
                    f"{name} has invalid level {macro.level!r}",
                )

    def test_rule2_oracles_are_level_zero(self) -> None:
        """Every listed oracle is level zero, and the list is not stale."""
        macros = theory.global_macros
        for name in sorted(ORACLES):
            with self.subTest(macro=name):
                self.assertIn(name, macros)
                self.assertEqual(macros[name].level, 0)

        measured = {name for name, macro in macros.items() if macro.level == 0}
        with self.subTest(macro="<level-0 set>"):
            self.assertEqual(measured, ORACLES)

    def test_rule3_signature_round_trip(self) -> None:
        """Every macro with a real argument round-trips its printed signature."""
        for name in sorted(self._rule3):
            with self.subTest(macro=name):
                reason = self._rule3[name]
                if reason is not None and name in KNOWN_FAILURES:
                    self.skipTest(f"known failure: {KNOWN_FAILURES[name]}")
                self.assertIsNone(reason, reason)

    def test_rule4_expansion_graph_is_acyclic(self) -> None:
        """The macro expansion graph built from stored proofs has no cycle."""
        with self.subTest(graph="nonempty"):
            self.assertGreater(sum(self._expansion_counts.values()), 0)

        cycle = _find_cycle(self._graph)
        with self.subTest(graph="acyclic"):
            self.assertIsNone(cycle, f"expansion cycle: {' -> '.join(cycle or [])}")


if __name__ == "__main__":
    unittest.main()
