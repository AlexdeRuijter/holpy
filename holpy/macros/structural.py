"""Small structural macros that replace long chains of primitive steps.

* ``exI_list`` -- ``∃x1 ... xn. P x1 ... xn`` from ``P w1 ... wn``.
* ``conj_intro`` -- ``A1 ∧ ... ∧ An`` (right-nested) from ``A1 ... An``.
* ``conj_elim`` -- ``Ai`` from ``A1 ∧ ... ∧ An``.
* ``contr`` -- any ``C`` from ``A`` and ``¬A``.
* ``cases`` -- case analysis on several variables at once, one leaf per
  combination of constructors, built on :mod:`holpy.macros.induct`.

All are level 1, and their expansions use only primitive rules,
``theorem`` and the expandable ``beta_norm`` and ``induct`` macros.
Arguments are a single term or a list of terms, so they round-trip through
the JSON proof format.
"""

from __future__ import annotations

from typing import List, Tuple

from holpy.kernel.macro import Macro
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.term import Term, Var
from holpy.kernel.theory import register_macro
from holpy.kernel import theory
from holpy.macros.induct import default_rule, induct_cases, rule_shape


class StructuralException(Exception):
    """Raised when a structural macro does not apply."""


def _beta(pt: ProofTerm) -> ProofTerm:
    return ProofTerm("beta_norm", None, [pt])


@register_macro("exI_list")
class ExIListMacro(Macro):
    """``exI_list [goal, w1, ..., wn]``: prove ``goal = ∃x1 ... xn. body`` from
    ``body[w1/x1, ..., wn/xn]``.
    """

    def __init__(self) -> None:
        self.level = 1
        self.sig = List[Term]
        self.limit = None

    def get_proof_term(self, args, pts) -> ProofTerm:
        goal, ws = args[0], list(args[1:])
        if len(pts) != 1:
            raise StructuralException("exI_list: expects one fact")
        # Instances of the goal with the first i witnesses substituted, from
        # the outside in; the innermost one must be the given fact.
        layers = [goal]
        for w in ws:
            t = layers[-1]
            if not t.is_exists():
                raise StructuralException("exI_list: too many witnesses for %s" % goal)
            layers.append(t.arg.subst_bound(w))
        if pts[0].prop != layers[-1]:
            raise StructuralException("exI_list: fact is\n  %s\nexpected\n  %s"
                                      % (pts[0].prop, layers[-1]))
        pt = pts[0]
        for t, w in zip(reversed(layers[:-1]), reversed(ws)):
            inst = ProofTerm.theorem("exI").subst_type(a=w.get_type()).substitution(P=t.arg, a=w)
            pt = _beta(inst).implies_elim(pt)
        return pt


def conj_list(t: Term, n: int) -> List[Term]:
    """The n conjuncts of a right-nested conjunction."""
    res = []
    for _ in range(n - 1):
        if not t.is_conj():
            raise StructuralException("conj: %s has fewer than %d conjuncts" % (t, n))
        res.append(t.arg1)
        t = t.arg
    return res + [t]


@register_macro("conj_intro")
class ConjIntroMacro(Macro):
    """``conj_intro``: ``A1 ∧ ... ∧ An`` from ``A1, ..., An``."""

    def __init__(self) -> None:
        self.level = 1
        self.sig = None
        self.limit = None

    def get_proof_term(self, args, pts) -> ProofTerm:
        if not pts:
            raise StructuralException("conj_intro: expects at least one fact")
        pt = pts[-1]
        for p in reversed(pts[:-1]):
            pt = ProofTerm.theorem("conjI").substitution(A=p.prop, B=pt.prop) \
                .implies_elim(p, pt)
        return pt


@register_macro("conj_elim")
class ConjElimMacro(Macro):
    """``conj_elim Ai``: the first conjunct equal to ``Ai`` of a right-nested
    conjunction.
    """

    def __init__(self) -> None:
        self.level = 1
        self.sig = Term
        self.limit = None

    def get_proof_term(self, target: Term, pts) -> ProofTerm:
        if len(pts) != 1:
            raise StructuralException("conj_elim: expects one fact")
        pt = pts[0]
        while pt.prop != target:
            if not pt.prop.is_conj():
                raise StructuralException("conj_elim: %s is not a conjunct" % target)
            A, B = pt.prop.args
            if A == target:
                return ProofTerm.theorem("conjD1").substitution(A=A, B=B).implies_elim(pt)
            pt = ProofTerm.theorem("conjD2").substitution(A=A, B=B).implies_elim(pt)
        return pt


@register_macro("contr")
class ContrMacro(Macro):
    """``contr C``: ``C`` from ``¬A`` and ``A`` (in either order)."""

    def __init__(self) -> None:
        self.level = 1
        self.sig = Term
        self.limit = None

    def get_proof_term(self, concl: Term, pts) -> ProofTerm:
        if len(pts) != 2:
            raise StructuralException("contr: expects two facts")
        neg, pos = pts
        if not (neg.prop.is_not() and neg.prop.arg == pos.prop):
            pos, neg = neg, pos
        if not (neg.prop.is_not() and neg.prop.arg == pos.prop):
            raise StructuralException("contr: facts are not A and ¬A")
        return ProofTerm.theorem("negE_gen").substitution(A=pos.prop, C=concl) \
            .implies_elim(neg, pos)


def _fresh(nm: str, used: List[str]) -> str:
    """A name not in ``used``, written so that it parses back (x, x1, x2, ...)."""
    if nm not in used:
        return nm
    i = 1
    while nm + str(i) in used:
        i += 1
    return nm + str(i)


def _split_premise(prem: Term, raw: Term, used: List[str]) -> Tuple[List[Var], List[Term], Term]:
    """Open ``∀x̄. H̄ ⟶ c`` with fresh names; return (x̄, H̄, c).

    The numbers of quantifiers and hypotheses come from the uninstantiated
    rule premise ``raw``, so implications inside the goal stay in ``c``.
    """
    raw_xs, raw_body = raw.strip_forall()
    num_hyps = len(raw_body.strip_implies()[0])
    xs = []
    for _ in raw_xs:
        nm = _fresh(prem.arg.var_name, used)
        used.append(nm)
        x = Var(nm, prem.arg.var_T)
        xs.append(x)
        prem = prem.arg.subst_bound(x)
    Hs = []
    for _ in range(num_hyps):
        Hs.append(prem.arg1)
        prem = prem.arg
    return xs, Hs, prem


def _used_names(goal: Term, vs: List[Term]) -> List[str]:
    return [v.name for v in goal.get_vars()] + [v.name for v in vs]


def _cases_plan(goal: Term, vs: List[Term], used: List[str]):
    """Yield the tree of the split: (rule, var, [(xs, Hs, subtree), ...]) or a leaf."""
    if not vs:
        return goal
    v = vs[0]
    rule = default_rule(v.T)
    As, _, Bs, P, _ = rule_shape(theory.get_theorem(rule).prop)
    branches = []
    for raw, prem in zip(As + Bs, induct_cases(rule, v, goal)):
        if P.name not in {sv.name for sv in raw.get_svars()}:
            raise StructuralException("cases: rule %s has a side condition %s" % (rule, raw))
        xs, Hs, c = _split_premise(prem, raw, used)
        branches.append((xs, Hs, _cases_plan(c, vs[1:], used)))
    return (rule, v, goal, branches)


def _leaves(plan) -> List[Term]:
    if isinstance(plan, Term):
        return [plan]
    return [leaf for _, _, sub in plan[3] for leaf in _leaves(sub)]


def cases_leaves(goal: Term, vs: List[Term]) -> List[Term]:
    """The leaves of ``cases [goal, v1, ..., vk]``, in macro premise order."""
    return _leaves(_cases_plan(goal, vs, _used_names(goal, vs)))


@register_macro("cases")
class CasesMacro(Macro):
    """``cases [goal, v1, ..., vk]``: split each variable by its type's
    default rule (the ``var_induct`` theorem), one after the other.

    The facts are proofs of the leaves, in the order of
    :func:`cases_leaves`.  Constructor arguments get fresh names; induction
    hypotheses are discharged without being used, so this is case analysis.
    Hypotheses of the leaf proofs must not mention those fresh names; put
    assumptions about a split variable into the goal as implications.
    """

    def __init__(self) -> None:
        self.level = 1
        self.sig = List[Term]
        self.limit = None

    def get_proof_term(self, args, pts) -> ProofTerm:
        goal, vs = args[0], list(args[1:])
        for v in vs:
            if not v.is_var():
                raise StructuralException("cases: %s is not a variable" % v)
        plan = _cases_plan(goal, vs, _used_names(goal, vs))
        n = len(_leaves(plan))
        if len(pts) != n:
            raise StructuralException("cases: expected %d leaves, got %d" % (n, len(pts)))
        pts = list(pts)

        def build(plan) -> ProofTerm:
            if isinstance(plan, Term):
                pt = pts.pop(0)
                if pt.prop != plan:
                    raise StructuralException("cases: leaf is\n  %s\nexpected\n  %s"
                                              % (pt.prop, plan))
                return pt
            rule, v, g, branches = plan
            prem_pts = []
            for xs, Hs, sub in branches:
                pt = build(sub)
                for H in reversed(Hs):
                    pt = pt.implies_intr(H)
                for x in reversed(xs):
                    pt = pt.forall_intr(x)
                prem_pts.append(pt)
            return ProofTerm("induct", (rule, v, g), prem_pts)

        return build(plan)

