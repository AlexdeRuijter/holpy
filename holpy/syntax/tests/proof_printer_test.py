"""Round-trip tests for printing proof items with explicit types."""

from __future__ import annotations

import unittest

from holpy.kernel.term import SVar, Var
from holpy.kernel.type import BoolType, TFun, TVar, TyInst
from holpy.logic import basic, context
from holpy.syntax import parser, printer


class ProofPrinterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        basic.load_theory("logic_base")

    def test_typed_schematic_variable_parses(self) -> None:
        expected = SVar("P", TFun(TVar("a"), BoolType))
        self.assertEqual(parser.parse_term("(?P::'a => bool)"), expected)

    def test_proof_print_annotates_fresh_variable(self) -> None:
        term = Var("x", BoolType)
        text = printer.print_term(term, proof=True)
        self.assertEqual(text, "(x::bool)")
        with context.fresh_context(vars={}):
            self.assertEqual(parser.parse_term(text), term)

    def test_proof_print_annotates_fresh_schematic_variable(self) -> None:
        term = SVar("P", TFun(TVar("a"), BoolType))
        text = printer.print_term(term, proof=True)
        with context.fresh_context(vars={}):
            self.assertEqual(parser.parse_term(text), term)

    def test_proof_print_does_not_reuse_undeclared_context_cache(self) -> None:
        term = Var("z", BoolType)
        with context.fresh_context(vars={"z": BoolType}):
            self.assertEqual(printer.print_term(term, proof=True), "z")
        with context.fresh_context(vars={}):
            text = printer.print_term(term, proof=True)
            self.assertEqual(text, "(z::bool)")
            self.assertEqual(parser.parse_term(text), term)

    def test_tyinst_args_round_trip(self) -> None:
        tyinst = TyInst(a=TVar("a"))
        text = printer.print_str_args("subst_type", tyinst, None, proof=True)
        self.assertEqual(text, "{a: 'a}")
        self.assertEqual(parser.parse_args(TyInst, text), tyinst)


if __name__ == "__main__":
    unittest.main()
