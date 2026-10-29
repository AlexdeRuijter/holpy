# Author: Bohua Zhan

import unittest

from holpy.kernel.type import BoolType
from holpy.kernel.term import Term, Var, Eq
from holpy.kernel.thm import Thm
from holpy.kernel import theory
from holpy.kernel.proofterm import ProofTerm
from holpy.logic import conv
from holpy.logic.conv import beta_conv, else_conv, try_conv, abs_conv, top_conv, bottom_conv, \
    top_sweep_conv, arg_conv, rewr_conv, has_rewrite, ConvException
from holpy.syntax import parser, printer
from holpy.logic import context


def run_conv(self: unittest.TestCase, thy_name: str, cv: conv.Conv, *,
              vars=None, t: Term, t_res=None, failed=None, assms=None, limit=None):
    context.set_context(thy_name, vars=vars, limit=limit)

    if isinstance(t, str):
        t = parser.parse_term(t)
    assert isinstance(t, Term)

    if failed is not None:
        self.assertRaises(failed, cv.eval, t)
        self.assertRaises(failed, cv.get_proof_term, t)
        return

    if assms is not None:
        assms = tuple(parser.parse_term(assm) for assm in assms)
    else:
        assms = tuple()

    if isinstance(t_res, str):
        t_res = parser.parse_term(t_res)
    assert isinstance(t_res, Term)

    res_th = cv.eval(t)
    expected_th = Thm(Eq(t, t_res), assms)
    self.assertTrue(res_th.can_prove(expected_th),
        msg="\nExpected: %s\nGot %s" % (printer.print_thm(expected_th), printer.print_thm(res_th)))
    pt = cv.get_proof_term(t)
    prf = pt.export()
    self.assertEqual(theory.check_proof(prf), res_th)

class ConvTest(unittest.TestCase):
    def testBetaConv(self):
        run_conv(
            self, 'logic_base', beta_conv(),
            vars={"f": "'a => 'a => 'a", "x": "'a"},
            t="(%x. f x x) x",
            t_res="f x x"
        )

    def testBetaConvFail(self):
        run_conv(
            self, 'logic_base', beta_conv(),
            vars={"x": "'a"},
            t="x",
            failed=ConvException
        )

    def testTryConv(self):
        run_conv(
            self, 'logic_base', try_conv(beta_conv()),
            vars={"f": "'a => 'a => 'a", "x": "'a"},
            t="(%x. f x x) x",
            t_res="f x x"
        )

    def testTryConv2(self):
        run_conv(
            self, 'logic_base', try_conv(beta_conv()),
            vars={"x": "'a"},
            t="x",
            t_res="x"
        )

    def testRewrConv(self):
        run_conv(
            self, 'nat', rewr_conv("nat_plus_def_1"),
            vars={"x": "nat"},
            t="0 + x",
            t_res="x"
        )

    def testRewrConv2(self):
        run_conv(
            self, 'nat', rewr_conv("nat_plus_def_2"),
            vars={"x": "nat", "y": "nat"},
            t="Suc x + y",
            t_res="Suc (x + y)"
        )

    def testRewrConv3(self):
        run_conv(
            self, 'nat', rewr_conv("min_simp1"),
            vars={"x": "nat", "y": "nat"},
            t="min x y",
            t_res="x",
            failed=ConvException
        )

    def testRewrConv4(self):
        cond = parser.parse_term("(x::nat) <= y")
        run_conv(
            self, 'nat', rewr_conv("min_simp1", conds=[ProofTerm.sorry(Thm(cond))]),
            vars={"x": "nat", "y": "nat"},
            t="min x y",
            t_res="x"
        )

    def testRewrConv5(self):
        cond = Var('P', BoolType)
        run_conv(
            self, 'logic_base', rewr_conv('if_P', conds=[ProofTerm.sorry(Thm(cond))]),
            vars={'a': "'a", 'b': "'a", 'P': "bool"},
            t="if P then a else b",
            t_res="a"
        )

    def testRewrConv6(self):
        run_conv(
            self, 'set', rewr_conv('image_combine', sym=True),
            vars={'g': "'a => 'b", 'f': "'b => 'c", 's': "'a set"},
            t="image f (image g s)",
            t_res="image (f O g) s"
        )

    def testRewrConv7(self):
        run_conv(
            self, 'logic_base', rewr_conv('eta_conversion'),
            vars={'f': "'a => 'b"},
            t="%x. f x",
            t_res="f"
        )
    
    def testRewrConv8(self):
        run_conv(
            self, 'logic', rewr_conv('not_all'),
            vars={'P': "'a => bool"},
            t="~(!a. P a)",
            t_res="(?a. ~(P a))"
        )

    def testEtaConv(self):
        run_conv(
            self, 'logic_base', conv.eta_conv(),
            vars={'f': "'a => 'b"},
            t="%x. f x",
            t_res="f"
        )

    def testEtaConv2(self):
        run_conv(
            self, 'nat', conv.eta_conv(),
            vars={'x': 'nat'},
            t="%y. x + y",
            t_res='plus x'
        )

    def testAbsConv(self):
        run_conv(
            self, 'nat', abs_conv(rewr_conv('nat_plus_def_2')),
            vars={"x": "nat"},
            t="%y. Suc x + y",
            t_res="%y. Suc (x + y)"
        )

    def testTopBetaConv(self):
        run_conv(
            self, 'logic_base', top_conv(beta_conv()),
            vars={"f": "'a => 'a => 'a", "x": "'a"},
            t="(%x. f x x) ((%x. f x x) x)",
            t_res="f (f x x) (f x x)"
        )

    def testTopBetaConvAbs(self):
        run_conv(
            self, 'logic_base', top_conv(beta_conv()),
            vars={"f": "'a => 'a => 'a", "x": "'a"},
            t="%x. (%a. f a) x",
            t_res="%x. f x"
        )

    def testBottomBetaConv(self):
        run_conv(
            self, 'logic_base', bottom_conv(beta_conv()),
            vars={"f": "'a => 'a => 'a", "x": "'a"},
            t="(%x. f x x) ((%x. f x x) x)",
            t_res="f (f x x) (f x x)"
        )

    def testBottomBetaConv2(self):
        run_conv(
            self, 'logic_base', bottom_conv(beta_conv()),
            vars={'f': "'a => 'a => 'a", 'x': "'a"},
            t="(%x. %y. f x y) x x",
            t_res="f x x"
        )

    def testTopSweepConv(self):
        run_conv(
            self, 'real', top_sweep_conv(rewr_conv('real_poly_neg1')),
            vars={"x": "real"},
            t="-x",
            t_res="-1 * x"
        )

    def testTopSweepConv2(self):
        run_conv(
            self, 'set', top_sweep_conv(rewr_conv('if_P')),
            vars={'s': 'nat set'},
            t="(%x. if x Mem s then x else 0)",
            t_res="(%x. if x Mem s then x else 0)"
        )

    def testTopSweepConv3(self):
        cond = Var('P', BoolType)
        run_conv(
            self, 'logic_base', top_sweep_conv(rewr_conv('if_P', conds=[ProofTerm.sorry(Thm(cond))])),
            vars={'a': "'a", 'b': "'a", 'P': "bool"},
            t="(if P then a else b) = a",
            t_res="a = a"
        )

    def testTopSweepConv4(self):
        run_conv(
            self, 'set', top_sweep_conv(rewr_conv('image_combine', sym=True)),
            vars={'g': "'a => 'b", 'f': "'b => 'c", 's': "'a set"},
            t="image f (image g s) = t",
            t_res="image (f O g) s = t"
        )

    def testHasRewrite(self):
        test_data = [
            ("(0::nat) + x = x", "nat_plus_def_1", True),
            ("(0::nat) + x = x + 0", "add_0_right", True),
            ("%x. comp_fun g f x = y", "comp_fun_eval", True),
        ]

        context.set_context('function', vars={'x': 'nat', 'y': 'nat', 'f': 'nat => nat', 'g': 'nat => nat'})
        for t, th_name, res in test_data:
            t = parser.parse_term(t)
            self.assertEqual(has_rewrite(th_name, t), res)

    def testHasRewriteSym(self):
        test_data = [
            ("image f (image g s)", "image_combine", True),
            ("image h (image h t) = t", "image_combine", True),
        ]

        context.set_context('set', vars={'g': "'a => 'b", 'f': "'b => 'c", 's': "'a set", 'h': 'nat => nat', 't': 'nat set'})
        for t, th_name, res in test_data:
            t = parser.parse_term(t)
            self.assertEqual(has_rewrite(th_name, t, sym=True), res)


if __name__ == "__main__":
    unittest.main()
