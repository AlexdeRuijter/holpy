"""Round-trip tests for printing numeric applications and negations."""

import unittest

from holpy.logic import basic, context
from holpy.syntax import parser, printer
from holpy.syntax.settings import global_setting


class PrintNumeralRoundtripTest(unittest.TestCase):
    """Print a term and check that parsing the output gives the same term."""

    @classmethod
    def setUpClass(cls):
        basic.load_theory('transcendentals')

    def check_roundtrip(self, thy_name, source, expected):
        context.set_context(thy_name)
        term = parser.parse_term(source)

        with global_setting(unicode=False):
            printed = printer.print_term(term)

        self.assertEqual(printed, expected)
        self.assertEqual(parser.parse_term(printed), term)

    def test_of_nat_zero_as_application_argument(self):
        self.check_roundtrip(
            'real',
            'abs ((of_nat::nat => real) 0)',
            '(abs::real => real) (of_nat 0)')

    def test_of_nat_one_as_application_argument(self):
        self.check_roundtrip(
            'real',
            'abs ((of_nat::nat => real) 1)',
            '(abs::real => real) (of_nat 1)')

    def test_of_nat_two_as_application_argument_unchanged(self):
        self.check_roundtrip(
            'real',
            'abs ((of_nat::nat => real) 2)',
            '(abs::real => real) (of_nat 2)')

    def test_of_nat_zero_and_one_in_equalities(self):
        self.check_roundtrip(
            'real',
            'abs ((of_nat::nat => real) 1) = (of_nat::nat => real) 1',
            '(abs::real => real) (of_nat 1) = of_nat 1')
        self.check_roundtrip(
            'real',
            'abs ((of_nat::nat => real) 0) <= (of_nat::nat => real) 1',
            '(abs::real => real) (of_nat 0) <= of_nat 1')

    def test_integer_of_nat_one(self):
        self.check_roundtrip(
            'transcendentals',
            'integer ((of_nat::nat => real) 1)',
            'integer (of_nat 1)')

    def test_root_one_of_nat_applications(self):
        self.check_roundtrip(
            'transcendentals',
            'real_sgn ((of_nat::nat => real) 1) * '
            'exp (log ((of_nat::nat => real) 1) / (of_nat::nat => real) n) = '
            '(of_nat::nat => real) 1',
            'real_sgn (of_nat 1) * exp (log (of_nat 1) / of_nat n) = of_nat 1')

    def test_real_inverse_negative_zero(self):
        self.check_roundtrip(
            'real',
            'real_inverse (-0)',
            'real_inverse (-0)')
        self.check_roundtrip(
            'real',
            'real_inverse (-(0::real))',
            'real_inverse (-0)')

    def test_exp_log_negative_zero(self):
        self.check_roundtrip(
            'transcendentals',
            'exp (y * log (-0))',
            'exp (y * log (-0))')
        self.check_roundtrip(
            'transcendentals',
            'exp (y * log (-(0::real)))',
            'exp (y * log (-0))')


if __name__ == '__main__':
    unittest.main()
