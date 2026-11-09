"""Regression test for variable scoping in proof parsing."""

from __future__ import annotations

import unittest

from holpy.logic import basic, context
from holpy.server import server
from holpy.syntax import parser


class ParseProofScopeTest(unittest.TestCase):
    def test_subproof_variable_does_not_shadow_outer_variable(self) -> None:
        """A subproof variable of another type must not leak to outer lines."""
        basic.load_theory('nat')
        context.set_context('nat', vars={'x': 'nat'})
        proof = [
            {'id': '0', 'rule': 'subproof', 'args': '', 'prevs': [], 'th': ''},
            {'id': '0.0', 'rule': 'variable', 'args': 'x, bool', 'prevs': [], 'th': ''},
            {'id': '0.1', 'rule': 'reflexive', 'args': 'x', 'prevs': [], 'th': '⊢ x = x'},
            {'id': '1', 'rule': 'reflexive', 'args': 'Suc x', 'prevs': [],
             'th': '⊢ Suc x = Suc x'},
        ]

        state = server.parse_proof(proof)

        self.assertEqual(state.check_proof(), parser.parse_thm('⊢ Suc x = Suc x'))
        self.assertEqual(context.ctxt.vars['x'], parser.parse_type('nat'))

    def test_closing_intros_sees_subproof_variable(self) -> None:
        """The intros line closing a subproof may mention variables declared in it."""
        basic.load_theory('nat')
        context.set_context('nat', vars={'x': 'nat'})
        proof = [
            {'id': '0', 'rule': 'subproof', 'args': '', 'prevs': [], 'th': ''},
            {'id': '0.0', 'rule': 'variable', 'args': 'y, nat', 'prevs': [], 'th': ''},
            {'id': '0.1', 'rule': 'reflexive', 'args': 'y', 'prevs': [], 'th': '⊢ y = y'},
            {'id': '0.2', 'rule': 'intros', 'args': 'y = y', 'prevs': ['0.0', '0.1'],
             'th': ''},
        ]

        state = server.parse_proof(proof)

        self.assertIsNotNone(state.prf)
        self.assertNotIn('y', context.ctxt.vars)


    def test_closing_intros_theorem_uses_enclosing_variable(self) -> None:
        """The theorem of the closing intros line is read in the enclosing scope."""
        basic.load_theory('nat')
        context.set_context('nat', vars={'x': 'nat'})
        proof = [
            {'id': '0', 'rule': 'subproof', 'args': '', 'prevs': [], 'th': ''},
            {'id': '0.0', 'rule': 'variable', 'args': 'x, bool', 'prevs': [], 'th': ''},
            {'id': '0.1', 'rule': 'reflexive', 'args': 'x', 'prevs': [], 'th': '⊢ x = x'},
            {'id': '0.2', 'rule': 'intros', 'args': '', 'prevs': ['0.0', '0.1'],
             'th': 'Suc x = Suc x ⊢ ∀x::bool. x = x'},
        ]

        state = server.parse_proof(proof)

        self.assertEqual(state.check_proof(),
                         parser.parse_thm('Suc x = Suc x ⊢ ∀x::bool. x = x'))
        self.assertEqual(context.ctxt.vars['x'], parser.parse_type('nat'))


if __name__ == '__main__':
    unittest.main()
