# Author: Bohua Zhan

import unittest
from pathlib import Path

from holpy.logic import basic
from holpy.imperative import imp
from holpy.imperative.parser import parse_com, process_file
from holpy.syntax import parser

basic.load_theory('hoare')


class HoareParserTest(unittest.TestCase):
    def testHoareParser(self):
        test_data = [
            ("while (a != 5) { b := b + 7; a := a + 1 }",
             "While (%s. ~s (0::nat) = (5::nat)) (%s. true) (Seq (Assign 1 (%s. s 1 + 7)) (Assign 0 (%s. s 0 + 1)))"),

            ("if (a == 0) then a := a + 1 else skip",
             "Cond (%s. s (0::nat) = (0::nat)) (Assign 0 (%s. s 0 + 1)) Skip")
        ]

        for s, res in test_data:
            t = parse_com(s)
            t_res = parser.parse_term(res)
            self.assertEqual(t, t_res)

    def testParseFile(self):
        output = Path(basic.user_file("hoare_test_output"))
        original = output.read_text(encoding='utf-8') if output.exists() else None
        try:
            process_file("test", "hoare_test_output")
        finally:
            # process_file writes into the bundled library; keep the checkout clean.
            if original is None:
                output.unlink(missing_ok=True)
            else:
                output.write_text(original, encoding='utf-8')


if __name__ == "__main__":
    unittest.main()
