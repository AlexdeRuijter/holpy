# Author: Bohua Zhan

import unittest

from holpy.kernel.type import NatType
from holpy.kernel.term import Eq, Nat
from holpy.kernel.thm import Thm
from holpy.kernel import theory
from holpy.data import nat
from holpy.data import interval
from holpy.data import set
from holpy.logic import basic


class IntervalTest(unittest.TestCase):
    def testNumsegConv(self):
        test_data = [
            (5, 4),
            (5, 5),
            (3, 5),
            (0, 10),
        ]

        basic.load_theory('iterate')
        for m, n in test_data:
            mt, nt = Nat(m), Nat(n)
            t = interval.mk_interval(mt, nt)
            pt = interval.numseg_conv().get_proof_term(t)
            rhs = set.mk_literal_set([Nat(i) for i in range(m, n+1)], NatType)
            prf = pt.export()
            self.assertEqual(theory.check_proof(prf), Thm(Eq(t, rhs)))


if __name__ == "__main__":
    unittest.main()
