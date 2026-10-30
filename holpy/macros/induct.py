"""One induction macro for every induction or case rule.

The ``induct`` macro applies any theorem of the shape::

    A1 ⟶ ... ⟶ Ak ⟶ ∀z1 ... zm. B1 ⟶ ... ⟶ Bl ⟶ ?P t

where ``?P`` is a schematic predicate and ``t`` is a pattern that matches
the induction variable.  ``m`` and ``l`` may be zero, so the generated
datatype rules ``<T>_induct`` (``... ⟶ ?P ?x``), rules ending in
``∀n. ?P n`` and rules with side conditions (``finite ?s ⟶ ...``) are all
one case.  Case-analysis rules are induction rules whose case proofs ignore
the hypotheses, so they are covered too, and so are rules registered for
types without structural induction, such as sign cases on ``real``.

Arguments are ``(rule, var, goal)`` with ``sig = Tuple[str, Term, Term]``;
they print as ``rule, var, goal`` and parse back with
:func:`holpy.syntax.parser.parse_args`.  The previous facts are proofs of the
instantiated premises in rule order: ``A1 ... Ak`` then ``B1 ... Bl``.
:func:`induct_cases` computes exactly these subgoals, so a tactic and the
macro can never disagree.

The macro is level 1.  Its expansion uses only ``theorem``,
``subst_type``, ``substitution``, ``implies_elim``, ``forall_elim`` and the
expandable ``beta_norm`` macro, so a stored ``induct`` line expands
mechanically to primitive kernel steps.
"""

from __future__ import annotations

__all__ = ["InductException", "rule_shape", "induct_cases", "default_rule", "InductMacro"]

from copy import copy
from typing import List, Tuple

from holpy.kernel import theory
from holpy.kernel.macro import Macro
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.term import Inst, Lambda, SVar, Term
from holpy.kernel.theory import register_macro
from holpy.kernel.thm import Thm
from holpy.kernel.type import Type, TypeMatchException
from holpy.logic import matcher


class InductException(Exception):
    """Raised when ``induct`` cannot apply a rule to a goal."""


def rule_shape(prop: Term) -> Tuple[List[Term], List[Term], List[Term], Term, Term]:
    """Split an induction rule into its parts.

    Parameters
    ----------
    prop : Term
        Statement of the rule.

    Returns
    -------
    tuple
        ``(As, zs, Bs, P, t)``: the outer premises, the conclusion's
        quantified variables (as fresh schematic variables), the inner
        premises, the motive and the pattern it is applied to.

    Raises
    ------
    InductException
        If the conclusion is not ``?P t`` under quantifiers and premises.
    """
    As, C = prop.strip_implies()
    zs = []
    used = {v.name for v in prop.get_svars()}
    while C.is_forall():
        # Quantified conclusion variables become schematic so that the
        # pattern ``t`` can be matched against the induction variable.
        nm = C.arg.var_name
        while nm in used:
            nm = nm + "'"
        used.add(nm)
        z = SVar(nm, C.arg.var_T)
        zs.append(z)
        C = C.arg.subst_bound(z)
    Bs, C = C.strip_implies()
    P, ts = C.strip_comb()
    if not P.is_svar() or len(ts) != 1:
        raise InductException("induct: conclusion must have the form ?P t, found %s" % C)
    return As, zs, Bs, P, ts[0]


def _instantiate(rule: str, var: Term, goal: Term) -> Tuple[Inst, List[Term], List[Term], List[Term]]:
    """Instantiate ``rule`` with motive ``λvar. goal``.

    Returns
    -------
    tuple
        ``(inst, zs_inst, As, Bs)``: the instantiation of the rule's own
        schematic variables, the terms for the conclusion's quantified
        variables, and the instantiated, beta-normal outer and inner
        premises.

    Raises
    ------
    InductException
        If ``var`` is not a variable, or the rule does not fit the goal.
    """
    if not var.is_var():
        raise InductException("induct: induction variable must be a variable, found %s" % var)
    th = theory.get_theorem(rule)
    As, zs, Bs, P, t = rule_shape(th.prop)

    inst = Inst()
    try:
        P.T.match_incr(Lambda(var, goal).get_type(), inst.tyinst)
    except TypeMatchException:
        raise InductException("induct: rule %s does not apply to %s of type %s" % (rule, var, var.T))
    inst[P.name] = Lambda(var, goal)
    try:
        inst = matcher.first_order_match(t, var, inst)
    except matcher.MatchException:
        raise InductException("induct: rule %s cannot be applied to variable %s" % (rule, var))

    rule_svars = {v.name for v in th.prop.get_svars()}
    missing = sorted(rule_svars - set(inst.keys()))
    if missing:
        raise InductException("induct: rule %s leaves %s uninstantiated" % (rule, ", ".join(missing)))
    for stvar in th.prop.get_stvars():
        if stvar.name not in inst.tyinst:
            raise InductException("induct: rule %s leaves type variable %s uninstantiated"
                                  % (rule, stvar.name))

    zs_inst = [inst[z.name] for z in zs]
    rule_inst = Inst({k: v for k, v in inst.items() if k in rule_svars})
    rule_inst.tyinst = copy(inst.tyinst)
    return rule_inst, zs_inst, [A.subst_norm(inst) for A in As], [B.subst_norm(inst) for B in Bs]


def induct_cases(rule: str, var: Term, goal: Term) -> List[Term]:
    """Return the subgoals of ``induct (rule, var, goal)``, in premise order.

    Parameters
    ----------
    rule : str
        Name of the induction or case rule.
    var : Term
        The induction variable.
    goal : Term
        The statement to prove, containing ``var``.

    Returns
    -------
    List[Term]
        The instantiated premises ``A1 ... Ak, B1 ... Bl``.
    """
    _, _, As, Bs = _instantiate(rule, var, goal)
    return As + Bs


def default_rule(T: Type) -> str:
    """Return the default induction rule for type ``T``.

    This is the unique theorem with the ``var_induct`` attribute whose
    pattern has type ``T``.  Tactics use it to fill in an explicit rule
    name; stored proofs always name the rule, so checking them never
    depends on attribute lookup.

    Raises
    ------
    InductException
        If no rule, or more than one, is registered for ``T``.
    """
    found = []
    for name, attrs in theory.thy.get_data("attributes").items():
        if "var_induct" not in attrs:
            continue
        try:
            t = rule_shape(theory.get_theorem(name).prop)[4]
            t.get_type().match_incr(T, Inst().tyinst)
        except (InductException, TypeMatchException):
            continue
        found.append(name)
    if len(found) != 1:
        raise InductException("induct: %d default rules for type %s: %s" % (len(found), T, found))
    return found[0]


@register_macro("induct")
class InductMacro(Macro):
    """``induct (rule, var, goal)``: prove ``goal`` from the rule's premises.

    ``get_proof_term`` must be called directly; it cannot be driven through
    ``Macro.eval`` / ``Macro.expand`` because those call ``get_proof_term``
    with all previous proofs as one sequence ``(prevs,)``, which does not
    match this signature.

    Raises
    ------
    InductException
        If the rule or variable does not apply, the premises are wrong, or
        the derived proof does not equal the goal.
    TheoryException
        If the named rule is unregistered (raised by ``ProofTerm.theorem``
        through ``theory.get_theorem``).
    matcher.MatchException
        If the induction variable fails to match the rule's pattern.
    """

    def __init__(self) -> None:
        self.level = 1
        self.sig = Tuple[str, Term, Term]
        self.limit = None

    def eval(self, args, prevs) -> Thm:
        rule, var, goal = args
        prems = induct_cases(rule, var, goal)
        if len(prevs) != len(prems):
            raise InductException("induct: expected %d premises, got %d" % (len(prems), len(prevs)))
        for i, (prev, prem) in enumerate(zip(prevs, prems)):
            if prev.prop != prem:
                raise InductException("induct: premise %d is\n  %s\nexpected\n  %s" % (i, prev.prop, prem))
        return Thm(goal, *(prev.hyps for prev in prevs))

    def get_proof_term(self, args, pts) -> ProofTerm:
        """Build the proof term; must be called directly (see class docstring)."""
        rule, var, goal = args
        inst, zs_inst, As, Bs = _instantiate(rule, var, goal)
        if len(pts) != len(As) + len(Bs):
            raise InductException("induct: expected %d premises, got %d" % (len(As) + len(Bs), len(pts)))

        pt = ProofTerm.theorem(rule).subst_type(inst.tyinst).substitution(inst)
        # beta_norm is itself an expandable macro, so the whole expansion
        # stays expandable to primitive steps.
        if pt.prop.beta_norm() != pt.prop:
            # beta_norm cannot expand on a statement that is already normal.
            pt = ProofTerm("beta_norm", None, [pt])
        # Discharge premises one at a time, counted from the rule rather
        # than from the instantiated statement, so implications inside the
        # goal are never mistaken for premises.
        for p in pts[:len(As)]:
            pt = pt.implies_elim(p)
        for z in zs_inst:
            pt = pt.forall_elim(z)
        for p in pts[len(As):]:
            pt = pt.implies_elim(p)
        if pt.prop != goal:
            raise InductException("induct: derived %s, expected %s" % (pt.prop, goal))
        return pt
