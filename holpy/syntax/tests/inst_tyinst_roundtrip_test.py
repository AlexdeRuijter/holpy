import unittest
from holpy.logic import basic
from holpy.kernel.term import Inst, TyInst
from holpy.kernel.type import TVar, NatType, BoolType
from holpy.syntax import printer, parser
from holpy.syntax.settings import global_setting

basic.load_theory('logic')

class InstTyinstRoundtripTest(unittest.TestCase):
    def test_roundtrip_term_only(self):
        from holpy.kernel.term import Const
        inst = Inst({'x': Const('true', BoolType)})
        s = printer.print_str_args('rule', inst, None)
        parsed = parser.parse_inst(str(s))
        self.assertEqual(dict(inst.items()), dict(parsed.items()))
        self.assertTrue(not parsed.tyinst)

    def test_roundtrip_type_only(self):
        inst = Inst()
        inst.tyinst = TyInst({'a': NatType})
        s = printer.print_str_args('rule', inst, None)
        parsed = parser.parse_inst(str(s))
        self.assertTrue(not parsed.items())
        self.assertEqual(str(inst.tyinst), str(parsed.tyinst))

    def test_roundtrip_both(self):
        from holpy.kernel.term import Const
        inst = Inst({'x': Const('true', BoolType)})
        inst.tyinst = TyInst({'a': NatType})
        s = printer.print_str_args('rule', inst, None)
        parsed = parser.parse_inst(str(s))
        self.assertEqual(dict(inst.items()), dict(parsed.items()))
        self.assertEqual(str(inst.tyinst), str(parsed.tyinst))

    def test_apply_theorem_for_finite_empty_tyinst(self):
        # Ensure apply_theorem_for with a type instantiation survives roundtrip
        from holpy.kernel.term import Inst, TyInst
        basic.load_theory('logic')
        # Construct an Inst with only a type variable mapping
        inst = Inst()
        inst.tyinst = TyInst({'a': TVar('b')})
        s = printer.print_str_args('apply_theorem_for', ("finite_empty", inst), None)
        # The printed args is a tuple representation; extract the braces part for parsing
        args_str = str(s)
        self.assertIn("'a", args_str)
        start = args_str.find('{')
        end = args_str.rfind('}')
        self.assertGreaterEqual(start, 0)
        self.assertGreaterEqual(end, 0)
        inst_part = args_str[start:end+1]
        parsed_inst = parser.parse_inst(inst_part)
        self.assertEqual(str(inst.tyinst), str(parsed_inst.tyinst))

if __name__ == '__main__':
    unittest.main()
