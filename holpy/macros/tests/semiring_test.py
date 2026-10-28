"""Tests for ``semiring_norm``: laws as theorem names, laws as hypotheses
(the abstract max-plus case), and a single AC operation."""

from __future__ import annotations

import json
import unittest

from holpy.kernel import theory
from holpy.kernel.proof import Proof
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.report import ProofReport
from holpy.kernel.thm import Thm
from holpy.logic import basic, context
from holpy.macros.semiring import SemiringException
from holpy.syntax import parser, printer

NAT_LAWS = ("add_comm add_assoc mult_comm mult_assoc distrib_l "
            "nat_plus_def_1 nat_times_def_1 mult_1_left")

ABSTRACT_VARS = {"add": "'a ⇒ 'a ⇒ 'a", "mul": "'a ⇒ 'a ⇒ 'a", "z": "'a",
                 "a": "'a", "b": "'a", "c": "'a"}
ABSTRACT_LAWS = [
    "∀x. ∀y. add x y = add y x",
    "∀x. ∀y. ∀z. add x (add y z) = add (add x y) z",
    "∀x. add x x = x",
    "∀x. ∀y. mul x y = mul y x",
    "∀x. ∀y. ∀z. mul (mul x y) z = mul x (mul y z)",
    "∀x. ∀y. ∀z. mul x (add y z) = add (mul x y) (mul x z)",
    "∀x. add z x = x",
    "∀x. mul x z = z",
]


class SemiringNormTest(unittest.TestCase):
    def prove(self, names, goal, hyps, vars):
        with context.fresh_context(vars=vars):
            g = parser.parse_term(goal)
            hs = [parser.parse_term(h) for h in hyps]
        pt = ProofTerm("semiring_norm", (names, g), [ProofTerm.assume(h) for h in hs])
        self.assertEqual(pt.prop, g)
        rpt = ProofReport()
        th = theory.check_proof(pt.export(), rpt)
        self.assertTrue(th.can_prove(Thm(g, *hs)))
        self.assertEqual(rpt.macros_eval, set())

        prf = pt.export()
        lines = json.loads(json.dumps(sum((printer.export_proof_item(i) for i in prf.items), [])))
        prf2 = Proof()
        with context.fresh_context(vars=vars):
            for line in lines:
                prf2.insert_item(parser.parse_proof_rule(line))
        self.assertEqual(theory.check_proof(prf2).prop, g)
        return rpt

    def testNatByName(self):
        basic.load_theory("nat")
        vars = {"a": "nat", "b": "nat", "c": "nat"}
        self.prove(NAT_LAWS, "(a + b) * (c + 1) = c * b + a + a * c + b", [], vars)
        self.prove(NAT_LAWS, "0 * a + (b + 0 * c) = b", [], vars)

    def testAbstractIdempotentByHypotheses(self):
        basic.load_theory("logic")
        # (a ⊕ b)² = a² ⊕ ab ⊕ b² in an idempotent semiring: the cross terms merge.
        self.prove("", "mul (add a b) (add a b) = add (mul a a) (add (mul b b) (mul a b))",
                   ABSTRACT_LAWS, ABSTRACT_VARS)
        # z is the additive unit and absorbs products.
        self.prove("", "add (mul z c) (add a (mul a z)) = a", ABSTRACT_LAWS, ABSTRACT_VARS)

    def testRightDistribAndUnitForms(self):
        basic.load_theory("logic")
        laws = ABSTRACT_LAWS[:5] + [
            "∀x. ∀y. ∀z. mul (add y z) x = add (mul y x) (mul z x)",
            "∀x. add x z = x",
            "∀x. mul z x = z"]
        self.prove("", "mul c (add a (add z b)) = add (mul b c) (mul c a)", laws, ABSTRACT_VARS)

    def testSingleACOperation(self):
        basic.load_theory("logic")
        self.prove("", "add a (add b (add c a)) = add (add c b) a", ABSTRACT_LAWS[:3],
                   ABSTRACT_VARS)

    def testFailure(self):
        basic.load_theory("logic")
        with context.fresh_context(vars=ABSTRACT_VARS):
            g = parser.parse_term("mul a b = add a b")
            hs = [ProofTerm.assume(parser.parse_term(h)) for h in ABSTRACT_LAWS]
        with self.assertRaises(SemiringException):
            ProofTerm("semiring_norm", ("", g), hs)


if __name__ == "__main__":
    unittest.main()
