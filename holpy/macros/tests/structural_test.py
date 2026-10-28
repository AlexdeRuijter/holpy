"""Tests for the structural macros: each proof is checked with every macro
expanded, and its stored lines are reloaded from JSON."""

from __future__ import annotations

import json
import unittest

from holpy.kernel import theory
from holpy.kernel.proof import Proof
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.report import ProofReport
from holpy.kernel.thm import Thm
from holpy.logic import basic, context
from holpy.macros.structural import StructuralException, cases_leaves
from holpy.macros.tests.induct_test import add_items
from holpy.syntax import parser, printer


class StructuralTest(unittest.TestCase):
    def check(self, rule, args, prevs, expected, vars):
        """Build ``rule`` from sorried prevs, check it fully and via JSON."""
        with context.fresh_context(vars=vars):
            parse = parser.parse_term
            args = parse(args) if isinstance(args, str) else \
                (None if args is None else [parse(a) for a in args])
            prevs = [ProofTerm.sorry(Thm(parse(p))) for p in prevs]
            expected = parse(expected)
            pt = ProofTerm(rule, args, prevs)
            self.assertEqual(pt.prop, expected)

            prf = pt.export()
            rpt = ProofReport()
            self.assertEqual(theory.check_proof(prf, rpt).prop, expected)
            self.assertEqual(rpt.macros_eval, set())
            self.assertIn(rule, rpt.macros_expand)

            lines = json.loads(json.dumps(sum((printer.export_proof_item(i) for i in prf.items), [])))
            prf2 = Proof()
            for line in lines:
                prf2.insert_item(parser.parse_proof_rule(line))
            self.assertEqual(theory.check_proof(prf2).prop, expected)

    def testExIList(self):
        basic.load_theory("nat")
        self.check("exI_list", ["∃x. ∃y. x + y = (3::nat)", "(1::nat)", "(2::nat)"], ["(1::nat) + 2 = 3"],
                   "∃x. ∃y. x + y = (3::nat)", {})
        self.check("exI_list", ["∃x. x ≤ (n::nat)", "n"], ["n ≤ (n::nat)"],
                   "∃x. x ≤ (n::nat)", {"n": "nat"})

    def testConj(self):
        basic.load_theory("logic")
        vars = {"A": "bool", "B": "bool", "C": "bool"}
        self.check("conj_intro", None, ["A", "B", "C"], "A ∧ B ∧ C", vars)
        self.check("conj_elim", "B", ["A ∧ B ∧ C"], "B", vars)
        self.check("conj_elim", "B ∧ C", ["A ∧ B ∧ C"], "B ∧ C", vars)
        self.check("conj_elim", "C", ["A ∧ B ∧ C"], "C", vars)

    def testContr(self):
        basic.load_theory("logic")
        vars = {"A": "bool", "C": "bool"}
        self.check("contr", "C", ["¬A", "A"], "C", vars)
        self.check("contr", "C", ["A", "¬A"], "C", vars)

    def testCasesTwoVariables(self):
        basic.load_theory("real")
        add_items({"ty": "type.ind", "name": "ereal", "args": [], "constrs": [
            {"name": "ereal_bot", "args": [], "type": "ereal"},
            {"name": "ereal_real", "args": ["r"], "type": "real ⇒ ereal"}]})
        vars = {"u": "ereal", "v": "ereal", "r": "real", "r1": "real", "r2": "real"}
        with context.fresh_context(vars=vars):
            leaves = [str(t) for t in cases_leaves(parser.parse_term("u = v ⟶ v = u"),
                                                   [parser.parse_term("u"), parser.parse_term("v")])]
        self.assertEqual(len(leaves), 4)
        self.check("cases", ["u = v ⟶ v = u", "u", "v"],
                   ["ereal_bot = ereal_bot ⟶ ereal_bot = ereal_bot",
                    "ereal_bot = ereal_real r ⟶ ereal_real r = ereal_bot",
                    "ereal_real r1 = ereal_bot ⟶ ereal_bot = ereal_real r1",
                    "ereal_real r1 = ereal_real r2 ⟶ ereal_real r2 = ereal_real r1"],
                   "u = v ⟶ v = u", vars)

    def testCasesNatDropsHypothesis(self):
        basic.load_theory("nat")
        self.check("cases", ["n + 0 = n", "n"], ["(0::nat) + 0 = 0", "Suc n1 + 0 = Suc n1"],
                   "n + 0 = n", {"n": "nat"})

    def testErrors(self):
        basic.load_theory("logic")
        with context.fresh_context(vars={"A": "bool", "B": "bool"}):
            A, B = parser.parse_term("A"), parser.parse_term("B")
            with self.assertRaises(StructuralException):
                ProofTerm("contr", B, [ProofTerm.sorry(Thm(A)), ProofTerm.sorry(Thm(B))])
            with self.assertRaises(StructuralException):
                ProofTerm("conj_elim", B, [ProofTerm.sorry(Thm(A))])


if __name__ == "__main__":
    unittest.main()
