"""Tests for holpy/util/poly.py."""

import unittest

from holpy.kernel.term import Var
from holpy.kernel.type import IntType

from holpy.util.poly import Monomial, Polynomial, collect_pairs


class CompareFstExpectedFailureTest(unittest.TestCase):
    @unittest.expectedFailure
    def test_polynomial_equality_tied(self):
        # compare_fst compares only the first factor; fix deferred past 0.1.0
        # Expected to be True but currently False because ordering is incomplete.
        x = Monomial(1, [("x", 1)])
        x2 = Monomial(1, [("x", 2)])
        self.assertEqual(Polynomial([x, x2]), Polynomial([x2, x]))

    def test_mon_le(self):
        a = Monomial(1, ())
        b = Monomial(2, ())
        self.assertTrue(a <= a)
        self.assertTrue(a <= b)
        self.assertFalse(b <= a)
        sorted_coeffs = sorted([Monomial(c, ()) for c in [3, 1, 2]])
        self.assertEqual([m.coeff for m in sorted_coeffs], [1, 2, 3])

    def test_collect_pairs_example(self):
        x = Var('x', IntType)
        y = Var('y', IntType)
        result = collect_pairs([(x, 1), (y, 2), (x, 3)])
        self.assertEqual(result, ((x, 4), (y, 2)))
