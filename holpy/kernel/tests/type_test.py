# Author: Bohua Zhan

import unittest

from holpy.kernel.type import STVar, TVar, TConst, TFun, BoolType, TyInst, TypeMatchException
from holpy.syntax.settings import global_setting

Ta = TVar("a")
Tb = TVar("b")
Tc = TVar("c")
STa = STVar("a")
STb = STVar("b")
STc = STVar("c")

class TypeTest(unittest.TestCase):
    def testReprType(self):
        test_data = [
            (Ta, "TVar(a)"),
            (TConst("bool"), "TConst(bool, [])"),
            (TConst("list", Ta), "TConst(list, [TVar(a)])"),
            (TConst("tree", Ta, Tb), "TConst(tree, [TVar(a), TVar(b)])"),
            (TConst("fun", Ta, Tb), "TConst(fun, [TVar(a), TVar(b)])"),
        ]

        for T, repr_T in test_data:
            self.assertEqual(repr(T), repr_T)

    def testPrintType(self):
        test_data = [
            (Ta, "'a"),
            (TVar("ab"), "'ab"),
            (TConst("bool"), "bool"),
            (TConst("list", Ta), "'a list"),
            (TConst("list", TConst("list", Ta)), "'a list list"),
            (TConst("tree", Ta, Tb), "('a, 'b) tree"),
            (TFun(Ta, Tb), "'a => 'b"),
            (TFun(Ta, Tb, Tc), "'a => 'b => 'c"),
            (TFun(TFun(Ta, Tb), Tc), "('a => 'b) => 'c"),
            (TFun(TConst("list", Ta), Tb), "'a list => 'b"),
            (TFun(Ta, TConst("list", Tb)), "'a => 'b list"),
            (TConst("list", TFun(Ta, Tb)), "('a => 'b) list"),
            (TConst("list", TConst("list", TFun(Ta, Tb))), "('a => 'b) list list"),
            (TFun(TConst("list", Ta), TConst("list", Tb)), "'a list => 'b list"),
            (TConst("list", TFun(TConst("list", Ta), Tb)), "('a list => 'b) list"),
        ]

        for T, str_T in test_data:
            with global_setting(unicode=False):
                self.assertEqual(str(T), str_T)

    def testTypeEq(self):
        test_data = [
            (Ta, Ta, True),
            (TVar("a"), Ta, True),
            (Ta, Tb, False),
            (STVar("a"), Ta, False),
            (TConst("list", Ta), TConst("list", Ta), True),
            (TConst("list", Ta), TConst("list", Tb), False),
            (TConst("fun", Ta, Tb), TFun(Ta, Tb), True),
        ]

        for T1, T2, res in test_data:
            self.assertEqual(T1 == T2, res)
            self.assertEqual(T2 == T1, res)

    def testTypeEqNonType(self):
        # None is unequal; any other non-Type still trips the assertion.
        self.assertFalse(BoolType.__eq__(None))
        self.assertRaises(AssertionError, BoolType.__eq__, "bool")

    def testIsFun(self):
        self.assertTrue(TFun(Ta, Tb).is_fun())
        self.assertTrue(TConst("fun", Ta, Tb).is_fun())
        self.assertFalse(BoolType.is_fun())
        self.assertFalse(TConst("list", Ta).is_fun())
        self.assertFalse(Ta.is_fun())
        self.assertFalse(STVar("a").is_fun())

    def testTFun(self):
        # The fast paths must build exactly what the general loop builds.
        self.assertEqual(TFun(Ta, Tb), TConst("fun", Ta, Tb))
        self.assertEqual(TFun(Ta, Tb, Tc),
                         TConst("fun", Ta, TConst("fun", Tb, Tc)))
        self.assertEqual(TFun(Ta, Tb, Tc), TFun(Ta, TFun(Tb, Tc)))
        self.assertEqual(
            TFun(Ta, Tb, Tc, BoolType),
            TConst("fun", Ta, TConst("fun", Tb, TConst("fun", Tc, BoolType))))
        self.assertEqual(TFun(BoolType, BoolType), TConst("fun", BoolType, BoolType))

    def testTFunFail(self):
        # A non-Type argument is still rejected by the runtime check.
        self.assertRaises(TypeError, TFun, Ta, "b")
        self.assertRaises(TypeError, TFun, Ta, Tb, "c")

    def testStripType(self):
        test_data = [
            (Ta, ([], Ta)),
            (TFun(Ta, Tb), ([Ta], Tb)),
            (TFun(Ta, Ta, Tb), ([Ta, Ta], Tb)),
        ]

        for T, res in test_data:
            self.assertEqual(T.strip_type(), res)

    def testSubst(self):
        test_data = [
            (STa, Tb),
            (STb, Ta),
            (TFun(STa, Tb), TFun(Tb, Tb)),
            (TFun(STa, STb), TFun(Tb, Ta)),
            (TConst("list", STa), TConst("list", Tb)),
        ]

        for T, res in test_data:
            self.assertEqual(T.subst(TyInst(a=Tb, b=Ta)), res)

    def testMatch(self):
        test_data = [
            (STa, Tb, {"a" : Tb}),
            (TFun(STa, STb), TFun(Tb,Ta), {"a" : Tb, "b" : Ta}),
            (STa, BoolType, {"a" : BoolType}),
            (TFun(STa, BoolType), TFun(BoolType, BoolType), {"a" : BoolType}),
        ]

        for pat, T, tyinst in test_data:
            self.assertEqual(pat.match(T), TyInst(tyinst))

    def testMatchFail(self):
        test_data = [
            (TFun(STa, STa), TFun(Ta,Tb)),
            (BoolType, Ta),
        ]
        
        for pat, T in test_data:
            self.assertRaises(TypeMatchException, pat.match, T)

    def testGetTVars(self):
        test_data = [
            (BoolType, []),
            (TFun(Ta,Ta), [Ta]),
            (TFun(Ta,Tb), [Ta, Tb]),
        ]

        for T, res in test_data:
            self.assertEqual(T.get_tvars(), res)

    def testGetTSubs(self):
        test_data = [
            (BoolType, [BoolType]),
            (TFun(Ta,Ta), [Ta, TFun(Ta,Ta)]),
            (TFun(Ta,Tb), [Ta, Tb, TFun(Ta,Tb)]),
        ]

        for T, res in test_data:
            self.assertEqual(T.get_tsubs(), res)


if __name__ == "__main__":
    unittest.main()
