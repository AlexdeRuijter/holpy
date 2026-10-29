# Author: Bohua Zhan

import unittest
from holpy.logic import auto
from holpy.logic.tests.logic_test import run_macro


class AutoTest(unittest.TestCase):
    def testSolve(self):
        test_data = [
            ("A --> B --> A & B"),
            ("A & B --> B & A"),
            ("A | B --> B | A"),
            ("A & B & C --> (A & B) & C"),
            ("A | B | C --> (A | B) | C")
        ]

        vars = {'A': 'bool', 'B': 'bool'}
        for expr in test_data:
            run_macro(self, 'logic_base', 'auto', vars=vars, args=expr, res=expr)


if __name__ == "__main__":
    unittest.main()
