# Author: Bohua Zhan

"""Parsing imperative programs into Com objects."""

from __future__ import annotations

import os
import json
from lark import Lark, Transformer, v_args

from holpy.kernel.type import TFun, BoolType
from holpy.kernel.term import Term, Var, Const, Abs, true
from holpy.logic import basic
from holpy.imperative import expr
from holpy.imperative import com


grammar = r"""
    ?expr: CNAME -> var_expr
        | expr "." CNAME -> field_expr
        | expr "[" expr "]" -> array_expr
        | INT -> num_expr
        | expr "+" expr -> plus_expr
        | "-" expr -> uminus_expr
        | expr "-" expr -> minus_expr
        | expr "*" expr -> times_expr
        | CNAME "(" expr ("," expr)* ")" -> fun_expr
        | "(" expr ")"

    ?atom_cond: expr "==" expr -> eq_cond
        | expr "!=" expr -> ineq_cond
        | expr "<=" expr -> less_eq_cond
        | expr "<" expr -> less_cond
        | "true" -> true_cond
        | "if" cond "then" cond "else" cond -> if_cond
        | "forall" CNAME "." cond -> forall_cond
        | "(" cond ")"

    ?neg: "~" atom_cond -> neg | atom_cond  // Negation: priority 40
    
    ?conj: neg "&" conj | neg     // Conjunction: priority 35

    ?disj: conj "|" disj | conj   // Disjunction: priority 30

    ?imp: disj "-->" imp | disj  // Implies: priority 25

    ?cond: imp

    ?cmd: "skip" -> skip_cmd
        | CNAME ":=" expr -> assign_cmd
        | "if" "(" cond ")" "then" cmd "else" cmd -> if_cmd
        | "while" "(" cond ")" "{" cmd "}" -> while_cmd
        | "while" "(" cond ")" "{" "[" cond "]" cmd "}" -> while_cmd_inv
        | cmd ";" cmd -> seq_cmd

    %import common.CNAME
    %import common.WS
    %import common.INT

    %ignore WS
"""

@v_args(inline=True)
class HoareTransformer(Transformer):
    """Lark transformer for imperative expressions and commands."""
    def __init__(self):
        """Initialize this object."""
        pass

    def var_expr(self, s):
        """Parse the var expr production."""
        """Process the var expr step."""
        return expr.Var(str(s))

    def field_expr(self, ident, fieldname):
        """Parse the field expr production."""
        """Process the field expr step."""
        return expr.Field(ident, fieldname)

    def array_expr(self, ident, idx):
        """Parse the array expr production."""
        """Process the array expr step."""
        return expr.ArrayElt(ident, idx)

    def num_expr(self, n):
        """Parse the num expr production."""
        """Process the num expr step."""
        return expr.Const(int(n))

    def plus_expr(self, e1, e2):
        """Parse the plus expr production."""
        """Process the plus expr step."""
        return expr.Op("+", e1, e2)

    def uminus_expr(self, e):
        """Parse the uminus expr production."""
        """Process the uminus expr step."""
        return expr.Op("-", e)

    def minus_expr(self, e1, e2):
        """Parse the minus expr production."""
        """Process the minus expr step."""
        return expr.Op("-", e1, e2)

    def times_expr(self, e1, e2):
        """Parse the times expr production."""
        """Process the times expr step."""
        return expr.Op("*", e1, e2)

    def fun_expr(self, fname, *args):
        """Parse the fun expr production."""
        """Process the fun expr step."""
        assert fname in expr.global_fnames, "Function %s not found" % fname
        return expr.Fun(fname, *args)

    def eq_cond(self, e1, e2):
        """Parse the eq cond production."""
        """Process the eq cond step."""
        return expr.Op("==", e1, e2)

    def ineq_cond(self, e1, e2):
        """Parse the ineq cond production."""
        """Process the ineq cond step."""
        return expr.Op("!=", e1, e2)

    def if_cond(self, cond, e1, e2):
        """Parse the if cond production."""
        """Process the if cond step."""
        return expr.ITE(cond, e1, e2)

    def conj(self, b1, b2):
        """Parse the conj production."""
        """Process the conj step."""
        return expr.Op("&", b1, b2)

    def disj(self, b1, b2):
        """Parse the disj production."""
        """Process the disj step."""
        return expr.Op("|", b1, b2)

    def imp(self, b1, b2):
        """Parse the imp production."""
        """Process the imp step."""
        return expr.Op("-->", b1, b2)

    def neg(self, b):
        """Parse the neg production."""
        """Process the neg step."""
        return expr.Op("~", b)

    def true_cond(self):
        """Parse the true cond production."""
        """Process the true cond step."""
        return expr.Const(True)

    def less_eq_cond(self, e1, e2):
        """Parse the less eq cond production."""
        """Process the less eq cond step."""
        return expr.Op("<=", e1, e2)

    def less_cond(self, e1, e2):
        """Parse the less cond production."""
        """Process the less cond step."""
        return expr.Op("<", e1, e2)

    def forall_cond(self, var_name, body):
        """Parse the forall cond production."""
        """Process the forall cond step."""
        return expr.Forall(expr.Var(var_name), body)

    def skip_cmd(self):
        """Parse the skip cmd production."""
        """Process the skip cmd step."""
        return com.Skip()

    def assign_cmd(self, v, e):
        """Parse the assign cmd production."""
        """Process the assign cmd step."""
        return com.Assign(expr.Var(str(v)), e)

    def if_cmd(self, b, c1, c2):
        """Parse the if cmd production."""
        """Process the if cmd step."""
        return com.Cond(b, c1, c2)

    def while_cmd(self, b, c):
        """Parse the while cmd production."""
        """Process the while cmd step."""
        return com.While(b, true, c)

    def while_cmd_inv(self, b, inv, c):
        """Parse the while cmd inv production."""
        """Process the while cmd inv step."""
        return com.While(b, inv, c)

    def seq_cmd(self, c1, c2):
        """Parse the seq cmd production."""
        """Process the seq cmd step."""
        return com.Seq(c1, c2)

cond_parser = Lark(grammar, start="cond", parser="lalr", transformer=HoareTransformer())
com_parser = Lark(grammar, start="cmd", parser="lalr", transformer=HoareTransformer())

def process_file(input):
    """Parse and process a program file."""
    basic.load_theory('hoare')

    dn = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dn, 'examples/' + input + '.json'), encoding='utf-8') as a:
        data = json.load(a)

    content = data['content']

    for run in content:
        if run['ty'] == 'vcg':
            c = com_parser.parse(run['com'])
            pre = cond_parser.parse(run['pre'])
            post = cond_parser.parse(run['post'])
            c.pre = [pre]
            c.compute_wp(post)
