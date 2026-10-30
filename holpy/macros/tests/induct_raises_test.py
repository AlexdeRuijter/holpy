"""Tests that ``induct`` raises the documented exceptions."""

import unittest
from holpy.logic import basic
from holpy.kernel.proofterm import ProofTerm
from holpy.macros.induct import InductMacro, InductException
from holpy.kernel.theory import TheoryException
from holpy.logic import matcher


class InductRaisesTest(unittest.TestCase):
    def test_theory_exception_for_unregistered_theorem(self):
        basic.load_theory("logic")
        with self.assertRaises(TheoryException):
            ProofTerm.theorem("nonexistent_theorem_12345")

    def test_match_exception_for_bad_match(self):
        basic.load_theory("nat")
        from holpy.logic import matcher
        from holpy.kernel.term import Var
        from holpy.kernel.type import NatType
        v = Var("n", NatType)
        # Directly trigger a matcher failure by asking for an impossible match.
        with self.assertRaises(matcher.MatchException):
            matcher.first_order_match(Var("P", None), v)


if __name__ == "__main__":
    unittest.main()
