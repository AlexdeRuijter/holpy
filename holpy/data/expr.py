# Author: Bohua Zhan

from holpy.kernel.type import TConst, TFun, BoolType, NatType
from holpy.kernel.term import Term, Const, Nat
from holpy.kernel.thm import Thm
from holpy.kernel.macro import Macro
from holpy.kernel.theory import register_macro
from holpy.logic import logic
from holpy.logic.logic import apply_theorem
from holpy.logic.tactic import MacroTactic
from holpy.data import nat
from holpy.data import function
from holpy.logic.conv import arg_conv
from holpy.kernel.proofterm import ProofTerm
from holpy.server.method import Method, register_method
from holpy.syntax import pprint, settings

"""Automation for arithmetic expressions."""

aexpT = TConst("aexp")

N = Const("N", TFun(NatType, aexpT))
V = Const("V", TFun(NatType, aexpT))
Plus = Const("Plus", TFun(aexpT, aexpT, aexpT))
Times = Const("Times", TFun(aexpT, aexpT, aexpT))

avalI = Const("avalI", TFun(TFun(NatType, NatType), aexpT, NatType, BoolType))


@register_macro('prove_avalI')
class prove_avalI_macro(Macro):
    """Prove a theorem of the form avalI s t n."""
    def __init__(self):
        self.level = 10
        self.sig = Term
        self.limit = 'avalI_times'

    def get_avalI_th(self, s, t) -> ProofTerm:
        """Given state s and expression t, return the proof of a theorem
        of the form avalI s t n.

        """
        def helper(t):
            if t.head == N:
                n, = t.args
                return apply_theorem("avalI_const", concl=avalI(s, N(n), n))
            elif t.head == V:
                x, = t.args
                pt = apply_theorem("avalI_var", concl=avalI(s, V(x), s(x)))
                return pt.on_arg(function.fun_upd_eval_conv())
            elif t.head == Plus:
                a1, a2 = t.args
                pt = apply_theorem("avalI_plus", helper(a1), helper(a2))
                return pt.on_arg(nat.nat_conv())
            elif t.head == Times:
                a1, a2 = t.args
                pt = apply_theorem("avalI_times", helper(a1), helper(a2))
                return pt.on_arg(nat.nat_conv())
            else:
                raise ValueError(f"Unsupported arithmetic expression: {t}")
        return helper(t)

    def get_avalI(self, s, t):
        """Given state s and expression t, return the integer n such that
        avalI s t n holds.

        """
        def helper(t):
            if t.head == N:
                return t.args[0].dest_number()
            elif t.head == V:
                x, = t.args
                res = function.fun_upd_eval_conv().eval(s(x)).prop.rhs
                assert res.is_number(), "get_avalI"
                return res.dest_number()
            elif t.head == Plus:
                a1, a2 = t.args
                return helper(a1) + helper(a2)
            elif t.head == Times:
                a1, a2 = t.args
                return helper(a1) * helper(a2)

        return helper(t)

    def eval(self, args, prevs):
        goal = args
        ths = prevs
        assert isinstance(goal, Term), "prove_avalI_macro"
        assert len(ths) == 0, "prove_avalI_macro"
        s, t, n = goal.args
        res = self.get_avalI(s, t)
        assert n == Nat(res), "prove_avalI_macro: wrong result"
        return Thm(goal)

    def can_eval(self, goal):
        assert isinstance(goal, Term), "prove_avalI_macro"
        if goal.head != avalI or len(goal.args) != 3:
            return False
        s, t, n = goal.args
        try:
            res = self.get_avalI(s, t)
        except AssertionError:
            return False

        return n == Nat(res)

    def get_proof_term(self, args, prevs) -> ProofTerm:
        goal = args
        pts = prevs
        assert isinstance(goal, Term), "prove_avalI_macro"
        assert len(pts) == 0, "prove_avalI_macro"
        s, t, n = goal.args
        pt = self.get_avalI_th(s, t)
        assert n == pt.prop.args[2], "prove_avalI_macro: wrong result."
        return pt


@register_method('prove_avalI')
class prove_avalI_method(Method):
    """Apply prove_avalI macro."""
    def __init__(self):
        self.sig = []
        self.limit = 'avalI_times'

    def search(self, state, id, prevs, data=None):  # type: ignore
        if data:
            return [data]

        if len(prevs) != 0:
            return []

        cur_item = state.get_proof_item(id)
        assert cur_item.th is not None
        cur_th = cur_item.th
        if prove_avalI_macro().can_eval(cur_th.prop):
            return [{}]
        else:
            return []

    def display_step(self, state, data):  # type: ignore
        return pprint.N("prove_avalI: ") + pprint.KWGreen("(solves)")  # type: ignore

    def apply(self, state, id, args, prevs):
        assert len(prevs) == 0, "prove_avalI_method"
        state.apply_tactic(id, MacroTactic('prove_avalI'))
