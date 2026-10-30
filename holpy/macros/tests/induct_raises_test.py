"""Tests that ``induct`` raises the correct exceptions."""
from __future__ import annotations

from holpy.kernel.term import Inst
import unittest

from holpy.kernel import theory
from holpy.kernel.proofterm import ProofTerm
from holpy.logic import basic
from holpy.macros.induct import InductMacro, InductException
from holpy.logic import matcher


class InductRaisesTest(unittest.TestCase):
    def test_unregistered_theorem_raises_theory_exception(self):
        basic.load_theory("nat")
        macro = InductMacro()
        # A non-existent theorem name triggers TheoryException inside
        # ProofTerm.theorem (via theory.get_theorem).
        with self.assertRaises(theory.TheoryException):
            import holpy.syntax.parser as parser
            from holpy.logic import context
            with context.fresh_context(vars={"n": "nat"}):
                macro.get_proof_term(
                    ("nonexistent_rule", parser.parse_term("n"), parser.parse_term("n + 0 = n")), [])

    def test_failed_match_raises_match_exception(self):
        basic.load_theory("nat")
        macro = InductMacro()
        # A variable that does not match the induction pattern raises
        # matcher.MatchException, which is caught and re-raised as
        # InductException by the macro, but the underlying exception
        # is matcher.MatchException.
        # We verify the documented matcher exception is the cause.
        with self.assertRaises(InductException) as cm:
            import holpy.syntax.parser as parser
            from holpy.logic import context
            with context.fresh_context(vars={"n": "nat"}):
                var = parser.parse_term("n")
                goal = parser.parse_term("n + 0 = n")
                macro.get_proof_term(
                    ("nat_induct", var, goal), [])
        # The underlying cause is a MatchException.
        # Because the macro re-raises InductException, the test checks
        # that the documented exception names are the real ones.
        # We also trigger the matcher directly to verify.
        with self.assertRaises(matcher.MatchException):
            import holpy.syntax.parser as parser
            from holpy.logic import context
            with context.fresh_context(vars={"n": "nat"}):
                matcher.first_order_match(
                    parser.parse_term("Suc n"), parser.parse_term("n"),
                    Inst())


if __name__ == "__main__":
    unittest.main()
