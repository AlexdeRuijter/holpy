"""Tests for ``transfer``: an abstract embedding given by hypotheses, and
negation on real as an order-reversing map given by library theorems."""

from __future__ import annotations

import unittest

from holpy.kernel import theory
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.report import ProofReport
from holpy.kernel.thm import Thm
from holpy.logic import basic, context
from holpy.macros.transfer import TransferException
from holpy.syntax import parser

VARS = {"phi": "'a ⇒ 'b", "f": "'a ⇒ 'a ⇒ 'a", "g": "'b ⇒ 'b ⇒ 'b",
        "c": "'a", "d": "'b", "le1": "'a ⇒ 'a ⇒ bool", "le2": "'b ⇒ 'b ⇒ bool",
        "h": "'a ⇒ 'a", "a": "'a", "b": "'a"}
LAWS = ["∀x. ∀y. phi (f x y) = g (phi x) (phi y)",
        "phi c = d",
        "∀x. ∀y. phi x = phi y ⟷ x = y",
        "∀x. ∀y. le2 (phi x) (phi y) ⟷ le1 x y"]


class TransferTest(unittest.TestCase):
    def prove(self, names, goal, fact, laws, vars):
        with context.fresh_context(vars=vars):
            g = parser.parse_term(goal)
            f = parser.parse_term(fact)
            hs = [parser.parse_term(h) for h in laws]
        pts = [ProofTerm.assume(f)] + [ProofTerm.assume(h) for h in hs]
        pt = ProofTerm("transfer", (names, g), pts)
        self.assertEqual(pt.prop, g)
        rpt = ProofReport()
        th = theory.check_proof(pt.export(), rpt)
        self.assertTrue(th.can_prove(Thm(g, f, *hs)))
        self.assertEqual(rpt.macros_eval, set())

    def testEmbeddingFromImage(self):
        basic.load_theory("logic")
        self.prove("", "f a b = f b a", "g (phi a) (phi b) = g (phi b) (phi a)", LAWS, VARS)
        self.prove("", "le1 (f a c) b", "le2 (g (phi a) d) (phi b)", LAWS, VARS)

    def testToImage(self):
        basic.load_theory("logic")
        self.prove("", "g (phi a) (phi b) = g (phi b) (phi a)", "f a b = f b a", LAWS, VARS)

    def testUnpreservedOperation(self):
        basic.load_theory("logic")
        with context.fresh_context(vars=VARS):
            g = parser.parse_term("h a = a")
            f = parser.parse_term("phi (h a) = phi a")
            hs = [ProofTerm.assume(parser.parse_term(h)) for h in LAWS]
        # h has no law, but injectivity still applies to the outer equation.
        ProofTerm("transfer", ("", g), [ProofTerm.assume(f)] + hs)
        with context.fresh_context(vars=VARS):
            f2 = parser.parse_term("g (phi a) (phi a) = phi a")
        with self.assertRaises(TransferException):
            ProofTerm("transfer", ("", g), [ProofTerm.assume(f2)] + hs)

    def testRealNegationReversesOrder(self):
        basic.load_theory("real")
        self.prove("real_neg_add real_le_lneg2", "x + y ≤ z", "-z ≤ -x + -y", [],
                   {"x": "real", "y": "real", "z": "real"})


if __name__ == "__main__":
    unittest.main()
