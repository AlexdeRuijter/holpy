import unittest
from holpy.kernel import theory, extension
from holpy.kernel.type import BoolType, NatType, STVar, TVar, TFun
from holpy.kernel.term import (
    SVar, Var, Eq, Implies, Inst, Abs, Bound, Comb, Const, Forall, Term, forall,
)
from holpy.kernel.proof import Proof
from holpy.kernel import thm
from holpy.kernel.thm import Thm, InvalidDerivationException


class Issue3OccursVarTest(unittest.TestCase):
    def setUp(self):
        self.prev_thy = theory.thy
        theory.thy = theory.EmptyTheory()

    def tearDown(self):
        theory.thy = self.prev_thy

    def test_issue3_reproduction_check_proof_raises(self):
        X, c = SVar('x', BoolType), Var('c', BoolType)
        prf = Proof()
        prf.add_item(0, 'assume', args=Eq(X, c))
        prf.add_item(1, 'forall_intr', args=X, prevs=[0])
        prf.add_item(2, 'implies_intr', args=Eq(X, c), prevs=[1])
        prf.add_item(3, 'substitution', args=Inst(x=c), prevs=[2])
        prf.add_item(4, 'reflexive', args=c)
        prf.add_item(5, 'implies_elim', prevs=[3, 4])
        prf.add_item(6, 'forall_elim', args=Eq(c, c), prevs=[5])
        prf.add_item(7, 'equal_elim', prevs=[6, 4])
        prf.add_item(8, 'forall_intr', args=c, prevs=[7])
        with self.assertRaises(Exception):
            theory.thy.check_proof(prf, no_gaps=True)

    def test_issue3_occurs_var_svar_in_itself(self):
        X = SVar('x', BoolType)
        self.assertTrue(X.occurs_var(X))

    def test_issue3_still_accepted_forall_intr_no_occur(self):
        # legitimate use should keep working
        x = Var('x', BoolType)
        th = Thm.reflexive(x)
        res = Thm.forall_intr(x, th)
        self.assertTrue(res.prop.is_forall())

    def test_issue3_still_accepted_forall_intr_var_with_other_hypothesis(self):
        x, y = Var('x', BoolType), Var('y', BoolType)
        th = Thm(Eq(x, x), y)
        res = Thm.forall_intr(x, th)
        self.assertEqual(res.hyps, (y,))

    def test_issue3_still_accepted_forall_intr_svar_no_occur(self):
        X, c = SVar('x', BoolType), Var('c', BoolType)
        th = Thm.reflexive(c)
        res = Thm.forall_intr(X, th)
        self.assertTrue(res.prop.is_forall())

    def test_issue3_still_accepted_abstraction_var(self):
        x = Var('x', BoolType)
        th = Thm.reflexive(x)
        res = Thm.abstraction(x, th)
        self.assertTrue(res.prop.is_equals())

    def test_issue3_still_accepted_abstraction_var_with_other_hypothesis(self):
        x, y = Var('x', BoolType), Var('y', BoolType)
        th = Thm(Eq(x, x), y)
        res = Thm.abstraction(x, th)
        self.assertEqual(res.hyps, (y,))


class Issue4SubstitutionTest(unittest.TestCase):
    def setUp(self):
        self.prev_thy = theory.thy
        theory.thy = theory.EmptyTheory()

    def tearDown(self):
        theory.thy = self.prev_thy

    def test_issue4_reproduction_check_proof_raises(self):
        Ta = TVar('a')
        x, a, b = Var('x', Ta), Var('a', Ta), Var('b', Ta)
        K = Abs('y', Ta, x)
        inst = Inst()
        inst.var_inst['x'] = Bound(0)
        prf = Proof()
        prf.add_item(0, 'beta_conv', args=K(a))
        prf.add_item(1, 'beta_conv', args=K(b))
        prf.add_item(2, 'symmetric', prevs=[1])
        prf.add_item(3, 'transitive', prevs=[0, 2])
        prf.add_item(4, 'substitution', args=inst, prevs=[3])
        prf.add_item(5, 'beta_conv', args=Abs('y', Ta, Bound(0))(a))
        prf.add_item(6, 'beta_conv', args=Abs('y', Ta, Bound(0))(b))
        prf.add_item(7, 'symmetric', prevs=[5])
        prf.add_item(8, 'transitive', prevs=[7, 4])
        prf.add_item(9, 'transitive', prevs=[8, 6])
        with self.assertRaises(theory.CheckProofException):
            theory.thy.check_proof(prf, no_gaps=True)

    def test_issue4_wrong_type_rejected(self):
        # If a value has wrong type it should be rejected.
        x = Var('x', BoolType)
        bad_inst = Inst()
        bad_inst.var_inst['x'] = Var('y', TVar('a'))
        th = Thm.reflexive(x)
        with self.assertRaises(InvalidDerivationException):
            Thm.substitution(bad_inst, th)

    def test_issue4_open_value_rejected(self):
        # A value with a bound variable loose under two abstractions is open.
        Ta = TVar('a')
        Tabba = TFun(Ta, TFun(Ta, Ta))
        x = Var('x', Tabba)
        bad_inst = Inst()
        bad_inst.var_inst['x'] = Abs('y', Ta, Abs('z', Ta, Bound(2)))
        th = Thm.reflexive(x)
        with self.assertRaises(InvalidDerivationException):
            Thm.substitution(bad_inst, th)

    def test_issue4_still_accepted_substitution_with_abs(self):
        # Legitimate substitution with a closed abstraction (lambda y. y).
        Ta = TVar('a')
        x = Var('x', TFun(Ta, Ta))
        lam = Abs('z', Ta, Bound(0))
        th = Thm.reflexive(x)
        inst = Inst()
        inst.var_inst['x'] = lam
        res = Thm.substitution(inst, th)
        self.assertEqual(res.prop, Eq(lam, lam))

    def test_issue4_still_accepted_schematic_with_type_inst(self):
        # A schematic instantiation together with a type instantiation.
        a = STVar('a')
        f = SVar('f', TFun(a, a))
        g = Var('g', TFun(NatType, NatType))
        th = Thm.reflexive(f)
        inst = Inst()
        inst.tyinst['a'] = NatType
        inst['f'] = g
        res = Thm.substitution(inst, th)
        self.assertEqual(res.prop, Eq(g, g))


class Issue5CheckedExtendTest(unittest.TestCase):
    def setUp(self):
        self.prev_thy = theory.thy
        theory.thy = theory.EmptyTheory()

    def tearDown(self):
        theory.thy = self.prev_thy

    def test_issue5_reproduction_checked_extend_raises_and_not_registered(self):
        Ta = TVar('a')
        x, y = Var('x', Ta), Var('y', Ta)
        prf = Proof()
        prf.add_item(0, 'reflexive', args=x)
        bogus = Thm(Eq(x, y))
        with self.assertRaises(theory.CheckProofException):
            theory.thy.checked_extend([extension.Theorem('bogus', bogus, prf)])
        with self.assertRaises(theory.TheoryException):
            theory.thy.get_theorem('bogus', svar=False)

    def test_issue5_still_accepted_correct_proof(self):
        Ta = TVar('a')
        x = Var('x', Ta)
        prf = Proof()
        prf.add_item(0, 'reflexive', args=x)
        th = Thm(Eq(x, x))
        theory.thy.checked_extend([extension.Theorem('good', th, prf)])
        self.assertEqual(theory.thy.get_theorem('good', svar=False).prop, th.prop)

    def test_issue5_still_accepted_proof_with_fewer_hypotheses(self):
        # The proof result has no hypotheses even though it uses an assumption.
        Ta = TVar('a')
        A, x = Var('A', BoolType), Var('x', Ta)
        prf = Proof()
        prf.add_item(0, 'assume', args=A)
        prf.add_item(1, 'reflexive', args=x)
        prf.add_item(2, 'implies_intr', args=A, prevs=[1])
        th = Thm(Implies(A, Eq(x, x)))
        theory.thy.checked_extend([extension.Theorem('fewer', th, prf)])
        self.assertEqual(theory.thy.get_theorem('fewer', svar=False).prop, th.prop)

    def test_issue5_rejects_stated_theorem_with_hypotheses(self):
        Ta = TVar('a')
        A, x = Var('A', BoolType), Var('x', Ta)
        prf = Proof()
        prf.add_item(0, 'reflexive', args=x)
        th = Thm(Eq(x, x), A)
        with self.assertRaises(theory.CheckProofException):
            theory.thy.checked_extend([extension.Theorem('with_hyp', th, prf)])
        with self.assertRaises(theory.TheoryException):
            theory.thy.get_theorem('with_hyp', svar=False)

    def test_issue5_still_accepted_no_proof_is_axiom(self):
        Ta = TVar('a')
        x = Var('x', Ta)
        th = Thm(Eq(x, x))
        rpt = theory.thy.checked_extend([extension.Theorem('axiom', th, None)])
        self.assertTrue(any(name == 'axiom' for name, _ in rpt.axioms))


class Issue6CheckTermTest(unittest.TestCase):
    def setUp(self):
        self.prev_thy = theory.thy
        theory.thy = theory.EmptyTheory()

    def tearDown(self):
        theory.thy = self.prev_thy

    def test_issue6_reproduction_check_proof_raises(self):
        Ta = TVar('a')
        n, m = Var('n', Ta), Var('m', Ta)
        fi = Const('implies', TFun(Ta, Ta, BoolType))
        prf = Proof()
        prf.add_item(0, 'assume', args=fi(n, m))
        prf.add_item(1, 'assume', args=fi(m, n))
        prf.add_item(2, 'equal_intr', prevs=[0, 1])
        prf.add_item(3, 'implies_intr', args=fi(m, n), prevs=[2])
        prf.add_item(4, 'implies_intr', args=fi(n, m), prevs=[3])
        with self.assertRaises(theory.CheckProofException):
            theory.thy.check_proof(prf, no_gaps=True)

    def test_issue6_reflexive_undeclared_constant_rejected(self):
        bad = Const('bad_const', BoolType)
        with self.assertRaises(theory.TheoryException):
            theory.thy.check_term(bad)

    def test_issue6_reflexive_undeclared_constant_proof_rejected(self):
        bad = Const('bad_const', BoolType)
        prf = Proof()
        prf.add_item(0, 'reflexive', args=bad)
        with self.assertRaises(theory.CheckProofException):
            theory.thy.check_proof(prf, no_gaps=True)

    def test_issue6_forall_elim_bad_equals_type_rejected(self):
        Ta, Tb = TVar('a'), TVar('b')
        T = TFun(Ta, Tb, BoolType)
        x = Var('x', T)
        bad_equals = Const('equals', T)
        prf = Proof()
        prf.add_item(0, 'assume', args=Forall(x, Eq(x, x)))
        prf.add_item(1, 'forall_elim', args=bad_equals, prevs=[0])
        with self.assertRaises(theory.CheckProofException):
            theory.thy.check_proof(prf, no_gaps=True)

    def test_issue6_check_term_svar_and_bound(self):
        self.assertIsNone(theory.thy.check_term(SVar('A', BoolType)))
        self.assertIsNone(theory.thy.check_term(Bound(0)))

    def test_issue6_still_accepted_polymorphic_constant(self):
        # equals at nat should work
        from holpy.kernel.type import NatType
        from holpy.kernel.term import equals
        eq_nat = equals(NatType)
        theory.thy.check_term(eq_nat)

    def test_issue6_still_accepted_polymorphic_constant_in_proof(self):
        from holpy.kernel.type import NatType
        n = Var('n', NatType)
        prf = Proof()
        prf.add_item(0, 'reflexive', args=n)
        th = theory.thy.check_proof(prf, no_gaps=True)
        self.assertEqual(th.prop, Eq(n, n))

    def test_issue6_still_accepted_final_theorem_line(self):
        # A proof whose last line cites a well-typed theory theorem is
        # accepted; the final-theorem guard validates it successfully.
        x = Var('x', BoolType)
        theory.thy.add_theorem('refl', Thm(Eq(x, x)))
        prf = Proof()
        prf.add_item(0, 'theorem', args='refl')
        th = theory.thy.check_proof(prf, no_gaps=True)
        self.assertEqual(th, theory.thy.get_theorem('refl'))

    def test_issue6_final_ill_typed_proposition_rejected(self):
        # Theorem lines are trusted by the per-rule checks; the final
        # theorem guard rejects a final proposition that uses an undeclared
        # constant.
        bad = Thm(Const('bad_const', BoolType))
        theory.thy.add_theorem('bad', bad)
        prf = Proof()
        prf.add_item(0, 'theorem', args='bad')
        with self.assertRaises(theory.CheckProofException):
            theory.thy.check_proof(prf, no_gaps=True)


class ExceptionHygieneTest(unittest.TestCase):
    """WS3-E: checker fixes for the exception types raised on bad input."""

    def setUp(self):
        self.prev_thy = theory.thy
        theory.thy = theory.EmptyTheory()
        self.prev_reflexive_rule = thm.primitive_deriv['reflexive']

    def tearDown(self):
        theory.thy = self.prev_thy
        thm.primitive_deriv['reflexive'] = self.prev_reflexive_rule

    def test_ws3e_forall_elim_eta_short_all_raises_invalid_derivation(self):
        # Issue #6 robustness: ``all P`` (eta-short) has a Var argument, not
        # an abstraction. It must be rejected, not raise AttributeError.
        P = Var('P', TFun(BoolType, BoolType))
        y = Var('y', BoolType)
        th = Thm(forall(BoolType)(P))
        with self.assertRaises(InvalidDerivationException):
            Thm.forall_elim(y, th)

    def test_ws3e_forall_elim_eta_short_all_in_check_proof(self):
        P = Var('P', TFun(BoolType, BoolType))
        y = Var('y', BoolType)
        prf = Proof()
        prf.add_item(0, 'assume', args=forall(BoolType)(P))
        prf.add_item(1, 'forall_elim', args=y, prevs=[0])
        with self.assertRaises(theory.CheckProofException):
            theory.thy.check_proof(prf, no_gaps=True)

    def test_ws3e_primitive_type_check_becomes_check_proof(self):
        # The argument of forall_elim passes check_term but is ill-typed, so
        # the primitive rule's own type check raises TypeCheckException.
        x = Var('x', BoolType)
        bad = Comb(x, x)
        prf = Proof()
        prf.add_item(0, 'assume', args=Forall(x, Eq(x, x)))
        prf.add_item(1, 'forall_elim', args=bad, prevs=[0])
        with self.assertRaises(theory.CheckProofException):
            theory.thy.check_proof(prf, no_gaps=True)

    def test_ws3e_type_error_from_broken_rule_propagates(self):
        # Only a wrong number of arguments is a CheckProofException; a
        # TypeError raised inside a primitive rule must reach the caller.
        def broken_rule(t):
            raise TypeError('deliberately broken primitive rule')

        thm.primitive_deriv['reflexive'] = (broken_rule, Term)
        x = Var('x', BoolType)
        prf = Proof()
        prf.add_item(0, 'reflexive', args=x)
        with self.assertRaises(TypeError):
            theory.thy.check_proof(prf, no_gaps=True)


if __name__ == '__main__':
    unittest.main()
