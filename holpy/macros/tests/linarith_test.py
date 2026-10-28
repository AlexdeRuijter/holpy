"""Tests for the ``real_linarith`` macro and its expandable numeral and
linear-normal-form conversions.

Each proof is checked at ``check_level=0``, so the kernel expands every
macro and the tests assert that no macro was evaluated as an oracle.
"""

from __future__ import annotations

import json
import unittest

from holpy.kernel import theory
from holpy.kernel.proof import Proof
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.report import ProofReport
from holpy.kernel.term import Real
from holpy.kernel.thm import Thm
from holpy.logic import basic, context
from holpy.syntax import parser, printer

VARS = {"x": "real", "y": "real", "z": "real", "a": "real", "s": "real", "e": "real"}


def setUpModule():
    basic.load_theory("real")


def full_check(test, pt):
    rpt = ProofReport()
    th = theory.check_proof(pt.export(), rpt)
    test.assertEqual(rpt.macros_eval, set())
    test.assertEqual(rpt.gaps, [])
    return th


class NumeralTest(unittest.TestCase):
    def testAddMul(self):
        from holpy.macros import linarith as L
        for a in [-7, -2, -1, 0, 1, 2, 5, 13]:
            for b in [-6, -1, 0, 1, 3, 13]:
                pt = L.num_add(Real(a) + Real(b))
                self.assertEqual(pt.rhs, Real(a + b))
                full_check(self, pt)
                pt = L.num_mul(Real(a) * Real(b))
                self.assertEqual(pt.rhs, Real(a * b))
                full_check(self, pt)

    def testPos(self):
        from holpy.macros import linarith as L
        for n in [1, 2, 7, 100]:
            pt = L.num_pos(n)
            self.assertEqual(pt.prop, Real(0) < Real(n))
            full_check(self, pt)


class LinNormTest(unittest.TestCase):
    def norm(self, s):
        from holpy.macros import linarith as L
        with context.fresh_context(vars=VARS):
            t = parser.parse_term(s)
        pt = L.lin_norm(t)
        full_check(self, pt)
        return pt.rhs

    def testCancel(self):
        self.assertEqual(self.norm("2 * (x - y) + 3 * y - x + 4 - (x + y)"), Real(4))
        self.assertEqual(self.norm("x - x"), Real(0))
        self.assertEqual(self.norm("-(-(x)) + -x + 3 * 0"), Real(0))

    def testCanonical(self):
        self.assertEqual(self.norm("y + 2 * x + 1"), self.norm("1 + x + y + x"))
        self.assertEqual(self.norm("x * y + 1 - x * y"), Real(1))


class RealLinarithTest(unittest.TestCase):
    def prove(self, hyps, goal):
        with context.fresh_context(vars=VARS):
            hs = [parser.parse_term(h) for h in hyps]
            g = parser.parse_term(goal)
        pts = [ProofTerm.assume(h) for h in hs]
        pt = ProofTerm("real_linarith", g, pts)
        self.assertEqual(pt.prop, g)
        # Hypotheses the certificate does not need are dropped.
        th = full_check(self, pt)
        self.assertEqual(pt.th, Thm(g, *hs))
        self.assertTrue(th.can_prove(Thm(g, *hs)))

        # The stored line round-trips through JSON.
        prf = pt.export()
        lines = json.loads(json.dumps(sum((printer.export_proof_item(i) for i in prf.items), [])))
        prf2 = Proof()
        with context.fresh_context(vars=VARS):
            for line in lines:
                prf2.insert_item(parser.parse_proof_rule(line))
        self.assertEqual(theory.check_proof(prf2), th)
        return pt

    def testTransitivity(self):
        self.prove(["x ≤ y", "y < z"], "x < z")
        self.prove(["x ≥ y", "y ≥ z"], "z ≤ x")

    def testScaling(self):
        self.prove(["2 * x + y ≤ 3", "x - y ≤ 1"], "3 * x ≤ 4")
        self.prove(["x < y"], "2 * x < 2 * y")

    def testEqualityAndFalse(self):
        self.prove(["x ≤ y", "y ≤ x + 0"], "x = y")
        self.prove(["x + 1 ≤ y", "y < x"], "false")
        self.prove(["x = 3", "y = x - 1"], "y = 2")

    def testNegatedHypothesis(self):
        self.prove(["¬(x ≤ y)", "y ≥ 5"], "x > 5")

    def testAtoms(self):
        # Non-linear terms are opaque atoms.
        self.prove(["x * y ≤ 1", "max x y ≥ x * y"], "x * y < max x y + 1")

    def testEsupLeaf(self):
        # The shape of the real leaves in the esup/einf lemmas.
        self.prove(["0 < e", "s - e < a", "a ≤ s"], "s < a + e")

    def testFractions(self):
        self.prove(["x ≤ 1 / 2", "y ≤ 1 / 3"], "x + y ≤ 5 / 6")
        self.prove(["x / 2 + y / 3 ≥ 1", "x ≤ 0"], "y ≥ 3")
        self.prove(["(x + y) / 4 < -(3 / 2)"], "x + y < -6")
        self.prove(["x = 2 / 3"], "3 * x = 2")

    def testFractionNumerals(self):
        from fractions import Fraction
        from holpy.macros import linarith as L
        t = Real(6) * (Real(Fraction(1, 2)) + Real(Fraction(-2, 3)))
        pt = L.push_denom(t).on_rhs(L.FunConv(L.lin_norm))
        self.assertEqual(pt.rhs, Real(-1))
        full_check(self, pt)

    def testEvalMatchesExpansion(self):
        from holpy.macros.linarith import LinarithException
        with context.fresh_context(vars=VARS):
            g = parser.parse_term("x < 1 / 2")
            h = parser.parse_term("2 * x ≤ 1")
        with self.assertRaises(LinarithException):
            ProofTerm("real_linarith", g, [ProofTerm.assume(h)])

    def testFailure(self):
        from holpy.macros.linarith import LinarithException
        with context.fresh_context(vars=VARS):
            g = parser.parse_term("x < y")
            h = parser.parse_term("x ≤ y")
        with self.assertRaises(LinarithException):
            ProofTerm("real_linarith", g, [ProofTerm.assume(h)])


if __name__ == "__main__":
    unittest.main()
