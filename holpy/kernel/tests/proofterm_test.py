# Author: Bohua Zhan

import unittest

from holpy.kernel.type import TVar, TFun
from holpy.kernel.term import Var, Term, Eq
from holpy.kernel.thm import Thm
from holpy.kernel.proof import Proof
from holpy.kernel import theory
from holpy.logic import basic
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.report import ProofReport
from holpy.data import real  # noqa: F401  (registers real_eq_comparison)
from holpy.logic import context
from holpy.syntax import parser

basic.load_theory('logic_base')

Ta = TVar("a")
x = Var("x", Ta)
y = Var("y", Ta)
z = Var("z", Ta)
f = Var("f", TFun(Ta,Ta,Ta))

class ProofTermTest(unittest.TestCase):
    def testExport(self):
        """Basic case."""
        pt1 = ProofTerm.assume(Eq(x,y))
        pt2 = ProofTerm.assume(Eq(y,z))
        pt3 = pt1.transitive(pt2)

        prf = pt3.export()
        self.assertEqual(len(prf.items), 3)
        self.assertEqual(theory.check_proof(prf), pt3.th)

    def testExport2(self):
        """Repeated theorems."""
        pt1 = ProofTerm.assume(Eq(x,y))
        pt2 = ProofTerm.reflexive(f)
        pt3 = pt2.combination(pt1)  # f x = f y
        pt4 = pt3.combination(pt1)  # f x x = f y y

        prf = pt4.export()
        self.assertEqual(len(prf.items), 4)
        self.assertEqual(theory.check_proof(prf), pt4.th)

    def testExport3(self):
        """Case with atoms."""
        pt1 = ProofTerm.atom(0, Thm(Eq(x,y)))
        pt2 = ProofTerm.atom(1, Thm(Eq(y,z)))
        pt3 = pt1.transitive(pt2)

        prf = Proof()
        prf.add_item(0, rule="sorry", th=Thm(Eq(x,y)))
        prf.add_item(1, rule="sorry", th=Thm(Eq(y,z)))
        pt3.export(prf=prf)

        self.assertEqual(theory.check_proof(prf), Thm(Eq(x,z)))

    def testCheckExpandsLevelNoneMacro(self):
        """A level-None macro is expanded, not evaluated, at check_level 0.

        real_eq_comparison has no trusted level, so check must call
        get_proof_term rather than eval even when the check level is zero.
        """
        basic.load_theory('real')
        context.set_context('real', vars={'x': 'real'})
        lhs = parser.parse_term('x >= 0')
        rhs = parser.parse_term('x + 0 >= 0')
        pt = ProofTerm('real_eq_comparison', Eq(lhs, rhs))

        rpt = ProofReport()
        pt.check(check_level=0, rpt=rpt)

        self.assertTrue(pt.checked)
        self.assertIn('real_eq_comparison', rpt.macros_expand)
        self.assertNotIn('real_eq_comparison', rpt.macros_eval)
        self.assertGreater(rpt.prim_steps, 0)


if __name__ == "__main__":
    unittest.main()
