# Author: Bohua Zhan

"""Tests for conversion of imperative expressions to HOL terms."""

from __future__ import annotations

import unittest

from holpy.data.list import ListType, length, nth
from holpy.imperative import expr
from holpy.kernel import term
from holpy.kernel.term import Int
from holpy.kernel.type import IntType


class ConvertHolTest(unittest.TestCase):
    def test_array_element(self):
        """ArrayElt converts to the `nth` application of its array and index."""
        array = expr.ArrayElt(expr.Var("a"), expr.Const(1))
        expected = nth(term.Var("a", ListType(IntType)), Int(1))
        self.assertEqual(array.convert_hol({"a": "int array"}), expected)

    def test_array_length(self):
        """Field('length') converts to the `length` application of its array."""
        array_length = expr.Field(expr.Var("a"), "length")
        expected = length(term.Var("a", ListType(IntType)))
        self.assertEqual(array_length.convert_hol({"a": "int array"}), expected)


if __name__ == "__main__":
    unittest.main()
