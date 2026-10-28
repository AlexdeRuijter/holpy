"""Transfer of statements along a structure map.

``transfer (names, goal)`` proves ``goal`` from one fact about the image of
a map ``φ``, using laws that say what ``φ`` preserves:

* relation laws ``(φ x R' φ y) ⟷ (x R y)`` -- injectivity
  (``φ x = φ y ⟷ x = y``), order embeddings (``φ x ≤ φ y ⟷ x ≤ y``), or
  order reversal (``-x ≤ -y ⟷ y ≤ x``);
* homomorphism laws ``φ (f x1 ... xn) = t`` with ``t`` built from the
  ``φ xi`` -- preserved operations and constants (``φ c = d``).

The first previous fact is the statement to transfer; the remaining
previous facts and the theorems in ``names`` (space separated) are laws.
The goal is rewritten with the relation laws (right to left), then the
homomorphism laws push ``φ`` inwards; the result must be the fact.  The
other direction (fact rewritten into the goal) is tried as well.

Only operations with a homomorphism law can be transferred, so a map that
preserves only some operations (an order embedding such as ``ereal ⇒
ehat``) transfers exactly the statements built from those.  An
isomorphism is the case where every operation has a law.

The macro is level 1; its expansion is rewriting with the laws.
"""

from __future__ import annotations

from typing import List, Tuple

from holpy.kernel.macro import Macro
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.term import SVar, Term
from holpy.kernel.theory import register_macro
from holpy.kernel.type import BoolType
from holpy.logic.conv import Conv, rewr_conv, top_conv


class TransferException(Exception):
    """Raised when ``transfer`` cannot relate the goal and the fact."""


def _schematic(pt: ProofTerm) -> ProofTerm:
    used = {v.name for v in pt.prop.get_svars()}
    while pt.prop.is_forall():
        nm = pt.prop.arg.var_name
        while nm in used:
            nm += "1"
        used.add(nm)
        pt = pt.forall_elim(SVar(nm, pt.prop.arg.var_T))
    return pt


def classify(pts: List[ProofTerm]) -> Tuple[List[ProofTerm], List[ProofTerm]]:
    """Split laws into relation laws (iff between relations) and homomorphism
    laws (equations)."""
    rels, homs = [], []
    for pt in pts:
        pt = _schematic(pt)
        p = pt.prop
        if not p.is_equals():
            raise TransferException("transfer: law is not an equation or iff: %s" % p)
        if p.lhs.get_type() == BoolType:
            rels.append(pt)
        else:
            homs.append(pt)
    return rels, homs


def transfer_conv(rels: List[ProofTerm], homs: List[ProofTerm]) -> Conv:
    """Rewrite source relations to image relations, then push φ inwards."""
    class _Conv(Conv):
        def get_proof_term(self, t: Term) -> ProofTerm:
            pt = ProofTerm.reflexive(t)
            if rels:
                pt = pt.on_rhs(top_conv(*[rewr_conv(r, sym=True) for r in rels]))
            if homs:
                pt = pt.on_rhs(top_conv(*[rewr_conv(h) for h in homs]))
            return pt
    return _Conv()


@register_macro("transfer")
class TransferMacro(Macro):
    """``transfer (names, goal)``: prove goal from its image under a structure map."""

    def __init__(self) -> None:
        self.level = 1
        self.sig = Tuple[str, Term]
        self.limit = None

    def get_proof_term(self, args, pts) -> ProofTerm:
        names, goal = args
        if not pts:
            raise TransferException("transfer: expects the fact to transfer")
        fact, law_pts = pts[0], list(pts[1:])
        law_pts = [ProofTerm.theorem(nm) for nm in names.split() if nm] + law_pts
        cv = transfer_conv(*classify(law_pts))

        g_pt = cv.get_proof_term(goal)            # goal = G'
        if g_pt.rhs == fact.prop:
            return g_pt.symmetric().equal_elim(fact)
        f_pt = cv.get_proof_term(fact.prop)       # fact = F'
        if f_pt.rhs == goal:
            return f_pt.equal_elim(fact)
        if f_pt.rhs == g_pt.rhs:
            return g_pt.symmetric().equal_elim(f_pt.equal_elim(fact))
        raise TransferException("transfer: the goal becomes\n  %s\nbut the fact is\n  %s"
                                % (g_pt.rhs, fact.prop))
