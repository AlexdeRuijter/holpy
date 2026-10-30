"""Tests for holpy/util/poly.py."""

import unittest

from holpy.util.poly import Monomial, Polynomial


class CompareFstExpectedFailureTest(unittest.TestCase):
    @unittest.expectedFailure
    def test_polynomial_equality_tied(self):
        # compare_fst compares only the first factor; fix deferred past 0.1.0
        # Expected to be True but currently False because ordering is incomplete.
        x = Monomial(1, [("x", 1)])
        x2 = Monomial(1, [("x", 2)])
        self.assertEqual(Polynomial([x, x2]), Polynomial([x2, x]))
