import unittest
from holpy.kernel.type import TVar, TConst, TyInst
from holpy.kernel.term import Inst
from holpy.syntax import parser, printer
from holpy.syntax.printer import print_str_args
from holpy.logic import basic

basic.load_theory('logic_base')
basic.load_theory('nat')

class InstRoundtripTest(unittest.TestCase):
    def test_term_only(self):
        from holpy.logic import context
        context.set_context('logic_base', vars={'a': 'bool', 'A': 'bool'})
        inst = parser.parse_inst('{a: A}')
        s = print_str_args('', inst, None)
        parsed = parser.parse_inst(s)
        self.assertEqual(dict(inst), dict(parsed))
        self.assertEqual(dict(inst.tyinst), dict(parsed.tyinst))

    def test_type_only(self):
        s = "{'a: 'b}"
        inst = parser.parse_inst(s)
        self.assertEqual(dict(inst.tyinst), {'a': TVar('b')})
        self.assertEqual(dict(inst), {})
        reparsed = parser.parse_inst(s)
        self.assertEqual(dict(inst.tyinst), dict(reparsed.tyinst))

    def test_combined(self):
        from holpy.logic import context
        context.set_context('logic_base', vars={'x': 'bool'})
        s = "{'a: 'b, x: true}"
        inst = parser.parse_inst(s)
        self.assertIn('a', dict(inst.tyinst))
        self.assertIn('x', dict(inst))
        reparsed = parser.parse_inst(s)
        self.assertEqual(dict(inst.tyinst), dict(reparsed.tyinst))
        self.assertEqual(dict(inst), dict(reparsed))

    def test_apply_theorem_for_tyinst(self):
        # Verify that apply_theorem_for with a type inst survives print/parse
        from holpy.logic import logic, context
        basic.load_theory('set')
        context.set_context('set', vars={'a': "'a", 'x': "'a"})
        thm = logic.theory.thy.get_theorem('finite_empty')
        inst = Inst()
        inst.tyinst = TyInst({'a': TVar('b')})
        pt = logic.apply_theorem('finite_empty', inst=inst)
        from holpy.syntax.printer import export_proof_item
        prf = pt.export()
        line = export_proof_item(prf.items[0])[0]
        args_str = line['args']
        self.assertIn("'a:", args_str)
        parsed = parser.parse_proof_rule(line)
        if isinstance(parsed.args, tuple) and len(parsed.args) == 2:
            new_inst = parsed.args[1]
            self.assertTrue(bool(new_inst.tyinst))

if __name__ == '__main__':
    unittest.main()
