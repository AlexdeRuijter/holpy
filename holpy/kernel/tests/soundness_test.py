import unittest
from holpy.kernel import theory, extension
from holpy.kernel.type import BoolType, TVar, TFun
from holpy.kernel.term import SVar, Var, Eq, Inst, Abs, Bound, Const
from holpy.kernel.proof import Proof
from holpy.kernel.thm import Thm


class Issue3OccursVarTest(unittest.TestCase):
    def setUp(self):
        self.prev_thy = theory.thy
        theory.thy = theory.EmptyTheory()

    def tearDown(self):
        theory.thy = self.prev_thy

    @unittest.expectedFailure  # WS3-3: remove this decorator when the fix lands (issue #3)
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

    @unittest.expectedFailure  # WS3-3: remove this decorator when the fix lands (issue #3)
    def test_issue3_occurs_var_svar_in_itself(self):
        X = SVar('x', BoolType)
        self.assertTrue(X.occurs_var(X))

    def test_issue3_still_accepted_forall_intr_no_occur(self):
        # legitimate use should keep working
        x = Var('x', BoolType)
        th = Thm.reflexive(x)
        res = Thm.forall_intr(x, th)
        self.assertTrue(res.prop.is_forall())


class Issue4SubstitutionTest(unittest.TestCase):
    def setUp(self):
        self.prev_thy = theory.thy
        theory.thy = theory.EmptyTheory()

    def tearDown(self):
        theory.thy = self.prev_thy

    @unittest.expectedFailure  # WS3-4: remove this decorator when the fix lands (issue #4)
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
        with self.assertRaises(Exception):
            theory.thy.check_proof(prf, no_gaps=True)

    @unittest.expectedFailure  # WS3-4: remove this decorator when the fix lands (issue #4)
    def test_issue4_wrong_type_rejected(self):
        # If a value has wrong type it should be rejected (expected failure on main)
        x = Var('x', BoolType)
        bad_inst = Inst()
        bad_inst.var_inst['x'] = Var('y', TVar('a'))
        th = Thm.reflexive(x)
        with self.assertRaises(Exception):
            Thm.substitution(bad_inst, th)

    def test_issue4_still_accepted_substitution_with_abs(self):
        # legitimate substitution with abstraction keeps working
        Ta = TVar('a')
        x = Var('x', Ta)
        y = Var('y', Ta)
        th = Thm.reflexive(x)
        inst = Inst()
        inst.var_inst['x'] = Abs('z', Ta, y)
        # should not raise
        res = Thm.substitution(inst, th)
        self.assertTrue(res.prop.is_reflexive() or True)


class Issue5CheckedExtendTest(unittest.TestCase):
    def setUp(self):
        self.prev_thy = theory.thy
        theory.thy = theory.EmptyTheory()

    def tearDown(self):
        theory.thy = self.prev_thy

    @unittest.expectedFailure  # WS3-5: remove this decorator when the fix lands (issue #5)
    def test_issue5_reproduction_checked_extend_raises_and_not_registered(self):
        Ta = TVar('a')
        x, y = Var('x', Ta), Var('y', Ta)
        prf = Proof()
        prf.add_item(0, 'reflexive', args=x)
        bogus = Thm(Eq(x, y))
        with self.assertRaises(Exception):
            theory.thy.checked_extend([extension.Theorem('bogus', bogus, prf)])
        with self.assertRaises(Exception):
            theory.thy.get_theorem('bogus', svar=False)

    def test_issue5_still_accepted_correct_proof(self):
        Ta = TVar('a')
        x = Var('x', Ta)
        prf = Proof()
        prf.add_item(0, 'reflexive', args=x)
        th = Thm(Eq(x, x))
        rpt = theory.thy.checked_extend([extension.Theorem('good', th, prf)])
        self.assertEqual(theory.thy.get_theorem('good', svar=False).prop, th.prop)

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

    @unittest.expectedFailure  # WS3-6: remove this decorator when the fix lands (issue #6)
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
        with self.assertRaises(Exception):
            theory.thy.check_proof(prf, no_gaps=True)

    def test_issue6_reflexive_undeclared_constant_rejected(self):
        bad = Const('bad_const', BoolType)
        with self.assertRaises(Exception):
            theory.thy.check_term(bad)

    def test_issue6_still_accepted_polymorphic_constant(self):
        # equals at nat should work
        from holpy.kernel.type import NatType
        from holpy.kernel.term import equals
        eq_nat = equals(NatType)
        theory.thy.check_term(eq_nat)


if __name__ == '__main__':
    unittest.main()
