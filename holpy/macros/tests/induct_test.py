"""Tests for the ``induct`` macro.

Every test checks three things: the subgoals ``induct_cases`` returns, a
kernel check that expands every macro down to primitive steps (no macro is
evaluated as an oracle), and a round trip of the stored proof through its
JSON form.
"""

from __future__ import annotations

import json
import unittest

from holpy.kernel import theory
from holpy.kernel.proof import Proof
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.report import ProofReport
from holpy.kernel.thm import Thm
from holpy.logic import basic, context
from holpy.macros.induct import InductException, default_rule, induct_cases
from holpy.server import items
from holpy.syntax import parser, printer


def add_items(*raw_items):
    """Extend the current theory with raw JSON items (test fixtures only)."""
    for raw in raw_items:
        item = items.parse_item(raw)
        assert item.error is None, item.error
        theory.thy.unchecked_extend(item.get_extension())


def json_lines(prf: Proof):
    lines = []
    for item in prf.items:
        lines.extend(printer.export_proof_item(item))
    return json.loads(json.dumps(lines))


class InductTest(unittest.TestCase):
    def run_induct(self, rule, var, goal, cases, *, vars, hyps=()):
        """Prove ``goal`` by ``induct`` from sorried cases and check everything."""
        with context.fresh_context(vars=vars):
            var_t = parser.parse_term(var)
            goal_t = parser.parse_term(goal)
            hyps_t = tuple(parser.parse_term(h) for h in hyps)
            expected = [parser.parse_term(c) for c in cases]

            self.assertEqual(induct_cases(rule, var_t, goal_t), expected)

            pts = [ProofTerm.sorry(Thm(c, hyps_t)) for c in expected]
            pt = ProofTerm("induct", (rule, var_t, goal_t), pts)
            self.assertEqual(pt.th, Thm(goal_t, hyps_t))

            # The checker expands every level >= 1 macro at check_level 0.
            prf = pt.export()
            rpt = ProofReport()
            self.assertEqual(theory.check_proof(prf, rpt), Thm(goal_t, hyps_t))
            self.assertEqual(rpt.macros_eval, set())
            self.assertIn("induct", rpt.macros_expand)
            self.assertEqual(len(rpt.gaps), len(expected))

            # Arguments survive printing and parsing.
            lines = json_lines(prf)
            induct_line = [line for line in lines if line["rule"] == "induct"]
            self.assertEqual(len(induct_line), 1)
            prf2 = Proof()
            for line in lines:
                prf2.insert_item(parser.parse_proof_rule(line))
            self.assertEqual(theory.check_proof(prf2), Thm(goal_t, hyps_t))
            return induct_line[0]

    def testNat(self):
        basic.load_theory("nat")
        line = self.run_induct(
            "nat_induct", "n", "n + 0 = n",
            ["(0::nat) + 0 = 0", "∀n. n + 0 = n ⟶ Suc n + 0 = Suc n"],
            vars={"n": "nat"})
        self.assertEqual(line["args"], "nat_induct, n, n + 0 = n")

    def testNatGoalWithImplication(self):
        # Regression: the stock apply_induct counted the goal's own
        # implications as premises of the rule.
        basic.load_theory("nat")
        self.run_induct(
            "nat_induct", "n", "m ≤ n ⟶ m ≤ n + k",
            ["m ≤ 0 ⟶ m ≤ 0 + k", "∀n. (m ≤ n ⟶ m ≤ n + k) ⟶ m ≤ Suc n ⟶ m ≤ Suc n + k"],
            vars={"n": "nat", "m": "nat", "k": "nat"})

    def testLegacyApplyInduct(self):
        basic.load_theory("nat")
        with context.fresh_context(vars={"n": "nat"}):
            var, goal = parser.parse_term("n"), parser.parse_term("n + 0 = n")
            pts = [ProofTerm.sorry(Thm(c)) for c in induct_cases("nat_induct", var, goal)]
            pt = ProofTerm("apply_induct", ("nat_induct", var, goal), pts)
            self.assertEqual(theory.check_proof(pt.export()), Thm(goal))

    def testListPolymorphic(self):
        basic.load_theory("list")
        self.run_induct(
            "list_induct", "xs", "xs @ [] = xs",
            ["([]::'a list) @ [] = []", "∀x::'a. ∀xs. xs @ [] = xs ⟶ (x # xs) @ [] = x # xs"],
            vars={"xs": "'a list"})

    def testSideCondition(self):
        basic.load_theory("set")
        self.run_induct(
            "finite_induct_strong", "s", "card s = card s",
            ["finite s", "card (∅::'a set) = card (∅::'a set)",
             "∀x::'a. ∀s1. card s1 = card s1 ⟶ ¬x ∈ s1 ⟶ finite s1 ⟶ card (insert x s1) = card (insert x s1)"],
            vars={"s": "'a set"})

    def testErealDatatype(self):
        basic.load_theory("real")
        add_items({"ty": "type.ind", "name": "ereal", "args": [], "constrs": [
            {"name": "ereal_bot", "args": [], "type": "ereal"},
            {"name": "ereal_real", "args": ["r"], "type": "real ⇒ ereal"}]})
        self.assertEqual(default_rule(parser.parse_type("ereal")), "ereal_induct")
        self.run_induct(
            "ereal_induct", "u", "u = u",
            ["ereal_bot = ereal_bot", "∀r. ereal_real r = ereal_real r"],
            vars={"u": "ereal"})

    def testThreeConstructorsWithHypothesis(self):
        # ehat = bot | real r | top, split under a boundedness hypothesis
        # that every case keeps.
        basic.load_theory("real")
        add_items({"ty": "type.ind", "name": "ehat", "args": [], "constrs": [
            {"name": "ehat_bot", "args": [], "type": "ehat"},
            {"name": "ehat_real", "args": ["r"], "type": "real ⇒ ehat"},
            {"name": "ehat_top", "args": [], "type": "ehat"}]})
        self.run_induct(
            "ehat_induct", "u", "u = u",
            ["ehat_bot = ehat_bot", "∀r. ehat_real r = ehat_real r", "ehat_top = ehat_top"],
            vars={"u": "ehat", "b": "real"}, hyps=["b ≥ 0"])

    def testRealRegisteredRule(self):
        # A non-datatype type gets case analysis from any registered rule.
        # The rule here is an unproved fixture; only the macro is tested.
        basic.load_theory("real")
        add_items({"ty": "thm", "name": "real_sign_cases", "vars": {"P": "real ⇒ bool", "y": "real"},
                   "prop": "(∀x. x < 0 ⟶ P x) ⟶ P 0 ⟶ (∀x. x > 0 ⟶ P x) ⟶ P y"})
        self.run_induct(
            "real_sign_cases", "y", "y * y ≥ 0",
            ["∀x::real. x < 0 ⟶ x * x ≥ 0", "(0::real) * 0 ≥ 0", "∀x::real. x > 0 ⟶ x * x ≥ 0"],
            vars={"y": "real"})

    def testQuantifiedConclusionWithInnerPremise(self):
        # Shape of prime's induct_coprime: ... ⟶ (∀n. 1 < n ⟶ P n).
        basic.load_theory("nat")
        add_items({"ty": "thm", "name": "gt1_induct", "vars": {"P": "nat ⇒ bool"},
                   "prop": "P 2 ⟶ (∀n. 1 < n ⟶ P n ⟶ P (n + 1)) ⟶ (∀n. 1 < n ⟶ P n)"})
        self.run_induct(
            "gt1_induct", "m", "m * m ≥ m",
            ["(2::nat) * 2 ≥ 2", "∀n::nat. 1 < n ⟶ n * n ≥ n ⟶ (n + 1) * (n + 1) ≥ n + 1", "1 < m"],
            vars={"m": "nat"})

    def testErrors(self):
        basic.load_theory("nat")
        with context.fresh_context(vars={"n": "nat"}):
            goal = parser.parse_term("n + 0 = n")
            with self.assertRaises(InductException):
                induct_cases("nat_induct", parser.parse_term("n + 0"), goal)
            with self.assertRaises(InductException):
                induct_cases("add_comm", parser.parse_term("n"), goal)
            pts = [ProofTerm.sorry(Thm(goal))]
            with self.assertRaises(InductException):
                ProofTerm("induct", ("nat_induct", parser.parse_term("n"), goal), pts)


if __name__ == "__main__":
    unittest.main()
