# Author: Bohua Zhan

"""Tree-shaped proof terms and their conversion to linear proofs.

A :class:`ProofTerm` stores a derivation as a tree of rule applications. This
is the convenient form for tactics and conversions; it can be exported to the
linear :class:`holpy.kernel.proof.Proof` representation expected by the
proof-state server and the theory checker.
"""

from __future__ import annotations

from typing import Any, List

from holpy.kernel.term import Term, Var, Inst
from holpy.kernel.type import Type, TyInst
from holpy.kernel.thm import Thm, primitive_deriv
from holpy.kernel.proof import Proof, ItemID
from holpy.kernel import theory
from holpy.util import typecheck


class TacticException(Exception):
    """Raised when a tactic cannot be applied to the current goal."""

    def __init__(self, err: str = ""):
        self.err = err

    def __str__(self) -> str:
        return self.err


class ProofTerm:
    """A derivation tree for a theorem.

    Attributes
    ----------
    rule : str
        Primitive derivation name or macro name.
    args : Any
        Arguments to the rule.
    prevs : list of ProofTerm
        Immediate subderivations.
    th : Thm
        Sequent proved by this node.
    gaps : list of Thm
        Statements still admitted as gaps below this node.
    """

    def __init__(self, rule: str, args: Any, prevs: list[ProofTerm] | None = None,
                 th: Thm | None = None):
        typecheck.checkinstance('ProofTerm', rule, str)

        self.rule = rule
        if prevs is None:
            prevs = []
        prev_ths = [prev.th for prev in prevs]
        if rule == 'atom':
            assert th is not None, "ProofTerm: must provide th for atom."
            self.th = th
        elif rule == 'sorry':
            assert th is not None, "ProofTerm: must provide th for sorry."
            self.th = th
        elif rule == 'variable':
            nm, T = args
            self.th = Thm.mk_VAR(Var(nm, T))
        elif rule == 'theorem':
            self.th = theory.get_theorem(args)
        elif rule in primitive_deriv:
            rule_fun, _ = primitive_deriv[rule]
            self.th = rule_fun(*prev_ths) if args is None else rule_fun(args, *prev_ths)
        else:
            macro = theory.get_macro(rule)
            if th is None:
                self.th = macro.eval(args, prev_ths)
            else:
                self.th = th

        self.args = args
        self.prevs: List[ProofTerm] = prevs
        if self.rule == 'sorry':
            self.gaps = [self.th]
        else:
            self.gaps = list(set(sum([prev.gaps for prev in self.prevs], [])))

        # Used for checking
        self.checked = False

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        res = "ProofTerm(%s)" % self.th
        if self.gaps:
            res += '\nGaps: ' + '\n      '.join(str(gap) for gap in self.gaps)
        return res

    @property
    def hyps(self) -> tuple[Term, ...]:
        """Hypotheses of the proof term."""
        return self.th.hyps

    @property
    def prop(self) -> Term:
        """Proposition of the proof term."""
        return self.th.prop

    @property
    def assums(self) -> list[Term]:
        """Antecedents of the proposition of the proof term."""
        return self.th.assums

    @property
    def concl(self) -> Term:
        """Conclusion of the proposition of the proof term."""
        return self.th.concl

    @property
    def lhs(self) -> Term:
        """Left side of an equality proof term."""
        return self.th.concl.lhs

    @property
    def rhs(self) -> Term:
        """Right side of an equality proof term."""
        return self.th.concl.rhs

    def is_equals(self) -> bool:
        """Return whether the proposition is an equality."""
        return self.prop.is_equals()

    def is_reflexive(self) -> bool:
        """Return whether the proposition is a reflexive equality."""
        return self.prop.is_reflexive()

    @staticmethod
    def atom(id: ItemID, th: Thm) -> ProofTerm:
        """Return a proof term referring to an existing proof item."""
        return ProofTerm('atom', id, [], th)

    @staticmethod
    def variable(nm: str, T: Type) -> ProofTerm:
        """Return the proof term for introducing a variable."""
        return ProofTerm("variable", (nm, T), [])

    @staticmethod
    def assume(A: Term) -> ProofTerm:
        """Return the proof term for assuming ``A``."""
        return ProofTerm("assume", A, [])

    @staticmethod
    def reflexive(x: Term) -> ProofTerm:
        """Return the proof term for ``x = x``."""
        return ProofTerm("reflexive", x, [])

    def symmetric(self) -> ProofTerm:
        """Reverse an equality proof term."""
        return ProofTerm("symmetric", None, [self])

    def transitive(self, *pts: ProofTerm) -> ProofTerm:
        """Chain this equality with one or more further equalities."""
        pt = self
        for eq_pt in pts:
            if pt.prop.is_reflexive():
                pt = eq_pt
            elif eq_pt.prop.is_reflexive():
                pass
            else:
                pt = ProofTerm("transitive", None, [pt, eq_pt])
        return pt

    def combination(self, pt2: ProofTerm) -> ProofTerm:
        """Apply congruence to two equality proof terms."""
        return ProofTerm("combination", None, [self, pt2])

    def equal_intr(self, pt2: ProofTerm) -> ProofTerm:
        """Build an equality from two implications."""
        return ProofTerm("equal_intr", None, [self, pt2])

    def equal_elim(self, pt2: ProofTerm) -> ProofTerm:
        """Rewrite ``pt2`` using this equality proof term."""
        if self.is_reflexive():
            return pt2
        return ProofTerm("equal_elim", None, [self, pt2])

    def implies_intr(self, A: Term) -> ProofTerm:
        """Discharge assumption ``A``."""
        return ProofTerm("implies_intr", A, [self])

    def implies_elim(self, *pts: ProofTerm) -> ProofTerm:
        """Apply modus ponens with one or more antecedent proofs."""
        pt = self
        for assum_pt in pts:
            pt = ProofTerm("implies_elim", None, [pt, assum_pt])
        return pt

    def subst_type(self, tyinst: TyInst | None = None, **kwargs: Type) -> ProofTerm:
        """Instantiate type variables."""
        if tyinst is None:
            tyinst = TyInst(**kwargs)
        if tyinst:
            return ProofTerm("subst_type", tyinst, [self])
        else:
            return self

    def substitution(self, inst: Inst | None = None, **kwargs: Term) -> ProofTerm:
        """Instantiate term variables."""
        if inst is None:
            inst = Inst(**kwargs)
        if inst:
            return ProofTerm("substitution", inst, [self])
        else:
            return self

    @staticmethod
    def beta_conv(x: Term) -> ProofTerm:
        """Return the beta-conversion proof term for ``x``."""
        return ProofTerm("beta_conv", x, [])

    def abstraction(self, x: Term) -> ProofTerm:
        """Abstract an equality over ``x``."""
        return ProofTerm("abstraction", x, [self])

    def forall_intr(self, x: Term) -> ProofTerm:
        """Universally quantify over ``x``."""
        return ProofTerm("forall_intr", x, [self])

    def forall_elim(self, s: Term) -> ProofTerm:
        """Instantiate a universal quantifier with ``s``."""
        return ProofTerm("forall_elim", s, [self])

    @staticmethod
    def theorem(th_name: str) -> ProofTerm:
        """Return a proof term referring to a named theorem."""
        return ProofTerm("theorem", th_name, [])

    @staticmethod
    def sorry(th: Thm) -> ProofTerm:
        """Return a proof term with an explicit gap."""
        typecheck.checkinstance('sorry', th, Thm)
        return ProofTerm("sorry", None, [], th)

    def check(self, *, check_level: int = 0, rpt: Any = None) -> None:
        """Check the proof term by expanding macros.

        ``rpt`` is a :class:`holpy.kernel.report.ProofReport` that receives
        step counts and gaps. The method mutates the ``checked`` flags of the
        nodes it visits and returns ``None``.
        """
        def rec(pt: ProofTerm):
            if pt.checked:
                return

            # Check dependencies first so that macro expansion sees checked
            # subderivations.
            for prev in pt.prevs:
                rec(prev)

            if pt.rule == 'atom':
                raise AssertionError("check proofterm: atom")
            elif pt.rule == 'sorry':
                rpt.add_gap(pt.th)
            elif pt.rule == 'variable':
                pass
            elif pt.rule == 'theorem':
                rpt.apply_theorem(pt.args)
            elif pt.rule in primitive_deriv:
                rpt.apply_primitive_deriv()
            else:
                macro = theory.get_macro(pt.rule)
                if macro.level <= check_level:
                    rpt.eval_macro(pt.rule)
                else:
                    expand_pt = macro.get_proof_term(pt.args, pt.prevs)
                    rpt.expand_macro(pt.rule)
                    rec(expand_pt)
            pt.checked = True

        rec(self)

    def export(self, prefix: ItemID | None = None, prf: Proof | None = None,
               subproof: bool = True) -> Proof:
        """Convert this tree into a linear proof.

        Parameters
        ----------
        prefix : ItemID, optional
            Identifier prefix for generated items.
        prf : Proof, optional
            Existing proof to append to. A fresh proof is created when absent.
        subproof : bool
            If true, nested derivations are exported as subproofs; otherwise
            they are flattened into the current proof.

        Returns
        -------
        Proof
            The exported linear proof.
        """
        def rec(pt: ProofTerm):
            # Should not call _export when self is already in seq_to_id
            assert pt.th not in seq_to_id, "export: th already found."

            # Should be called only on derivations
            assert pt.rule != 'atom', "export: atom"

            ids = []
            for prev in pt.prevs:
                if prev.rule == 'atom':
                    ids.append(prev.args)
                elif prev.th in seq_to_id:
                    ids.append(seq_to_id[prev.th])
                else:
                    rec(prev)
                    ids.append(prf.items[-1].id)

            if subproof:
                id = ItemID(prefix.id + (len(prf.items),))
            else:
                id = ItemID(prefix.id[:-1] + (prefix.id[-1] + len(prf.items),))

            seq_to_id[pt.th] = id
            prf.add_item(id, pt.rule, args=pt.args, prevs=ids, th=pt.th)

        # Current id prefix. Used in generating ids.
        if prefix is None:
            prefix = ItemID()

        # The currently built proof. Updated by the function.
        if prf is None:
            prf = Proof()

        # Mapping from existing sequents to ids.
        seq_to_id = dict()
        rec(self)
        return prf

    def on_prop(self, *cvs: Any) -> ProofTerm:
        """Rewrite the proposition using the given conversions."""
        pt = self
        for cv in cvs:
            eq_pt = cv.get_proof_term(pt.prop)
            pt = eq_pt.equal_elim(pt)
        return pt

    def on_arg(self, *cvs: Any) -> ProofTerm:
        """Rewrite the argument of an application in the proposition."""
        pt = self
        for cv in cvs:
            eq_pt = cv.get_proof_term(pt.prop.arg)
            eq_pt = ProofTerm.reflexive(pt.prop.fun).combination(eq_pt)
            pt = eq_pt.equal_elim(pt)
        return pt

    def on_lhs(self, *cvs: Any) -> ProofTerm:
        """Rewrite the left side of an equality proposition."""
        assert self.prop.is_equals(), "on_lhs: theorem is not an equality."
        pt = self
        for cv in cvs:
            eq_pt = cv.get_proof_term(pt.prop.lhs)
            pt = eq_pt.symmetric().transitive(pt)
        return pt

    def on_rhs(self, *cvs: Any) -> ProofTerm:
        """Rewrite the right side of an equality proposition."""
        assert self.prop.is_equals(), "on_rhs: theorem is not an equality."
        pt = self
        for cv in cvs:
            eq_pt = cv.get_proof_term(pt.prop.rhs)
            pt = pt.transitive(eq_pt)
        return pt

    def tac(self, tac: Any) -> ProofTerm:
        """Apply a tactic to the first remaining subgoal.

        Each tactic is applied to one subgoal; use :meth:`tacs` for a
        sequence, or the tactic layer's all-subgoal combinator for a tree.
        """
        if self.rule == 'sorry':
            return tac.get_proof_term(self.th)

        for i, prev in enumerate(self.prevs):
            if prev.gaps:
                new_prevs = self.prevs[:i] + [prev.tac(tac)] + self.prevs[i+1:]
                return ProofTerm(self.rule, self.args, prevs=new_prevs, th=self.th)

        raise TacticException('tac: no remaining subgoals')

    def tacs(self, *tacs: Any) -> ProofTerm:
        """Apply the given tactics in sequence."""
        pt = self
        for tac in tacs:
            pt = pt.tac(tac)
        return pt


def refl(t: Term) -> ProofTerm:
    """Return the proof term for ``t = t``."""
    return ProofTerm.reflexive(t)
