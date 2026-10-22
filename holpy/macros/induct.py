"""Generic structural-induction proof macro.

Provides :class:`InductMacro`, a reusable base for structural-induction
macros over user-defined datatypes.  Concrete types specialise it by
setting the class attribute ``induct_th_name`` to a registered
induction theorem of the shape::

    ⊢ P(base) ⟶ (<step premises>) ⟶ ∀z. P(z)

and registering the subclass.  The base class matches the first premise
against the caller's base-case proof to recover ``P``, discharges every
premise in order, and specialises ``∀z. P(z)`` to the caller's
induction variable.

Usage examples are documented in ``docs/WORKLOG.md``.
"""

from typing import Any, Optional

from holpy.kernel.macro import Macro
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.term import Inst, Term
from holpy.kernel.theory import register_macro
from holpy.logic import matcher


class InductMacro(Macro):
    """Generic structural-induction macro.

    Subclasses specialise the macro to a datatype by setting
    ``induct_th_name`` to the name of a registered induction theorem
    and, if the theorem does not end in ``∀z. P(z)``, overriding
    :meth:`_specialize`.  See :class:`ErealInductMacro` for a concrete
    example.

    Attributes
    ----------
    induct_th_name : Optional[str]
        Name of the registered induction theorem to instantiate.
        Subclasses must set this; it may also be supplied to
        ``__init__`` for one-off use.
    level : int
        Trust level (``1`` = safe: the kernel re-checks the proof
        term).
    sig : Optional[Any]
        Framework-provided signature slot; unused here.
    """

    induct_th_name: Optional[str] = None
    level: int
    sig: Optional[Any]

    def __init__(self, induct_th_name: Optional[str] = None) -> None:
        # Level 1 = safe: the macro expands into primitive inferences
        # so the kernel can independently re-check the proof term.
        self.level = 1
        self.sig = None
        if induct_th_name is not None:
            self.induct_th_name = induct_th_name

    def get_proof_term(self, var: Term, *premise_pts: ProofTerm) -> ProofTerm:
        """Build a proof term by structural induction on ``var``.

        Parameters
        ----------
        var : Term
            The induction variable used to specialise the final
            ``∀z. P(z)`` conclusion.
        *premise_pts : ProofTerm
            Proofs for the induction theorem's premises, in order.
            The first must prove the base case; its proposition
            determines the predicate ``P`` used to instantiate the
            theorem.  Remaining proofs discharge the step cases.

        Returns
        -------
        ProofTerm
            Proof of ``P(var)``.

        Raises
        ------
        ValueError
            If ``induct_th_name`` is unset, or if no ``premise_pts``
            are supplied.
        KeyError
            If ``induct_th_name`` does not name a registered theorem.
        """
        if self.induct_th_name is None:
            raise ValueError(
                "InductMacro.induct_th_name must be set by a subclass "
                "or passed to __init__ before use"
            )
        if not premise_pts:
            raise ValueError("at least one premise proof (the base case) is required")

        induct_pt = ProofTerm.theorem(self.induct_th_name)

        # Induction theorems have the form P(base) ⟶ ... ⟶ ∀z. P(z).
        # Matching the first premise against the caller's base-case
        # proposition recovers P so the whole implication chain can be
        # instantiated uniformly, regardless of how many step premises
        # a particular datatype contributes.
        base_assum, _ = induct_pt.prop.strip_implies()
        inst = Inst()
        inst = matcher.first_order_match(base_assum, premise_pts[0].prop, inst)
        induct_pt = induct_pt.substitution(inst)

        for premise_pt in premise_pts:
            induct_pt = induct_pt.implies_elim(premise_pt)

        return self._specialize(induct_pt, var)

    def _specialize(self, pt: ProofTerm, var: Term) -> ProofTerm:
        """Specialise the quantified conclusion to ``var``.

        Hook for subclasses whose induction theorem does not end in
        ``∀z. P(z)``.  The default implementation performs a
        ``forall_elim``.

        Parameters
        ----------
        pt : ProofTerm
            Proof term whose conclusion is ``∀z. P(z)``.
        var : Term
            Term to instantiate ``z`` with.

        Returns
        -------
        ProofTerm
            Proof of ``P(var)``.
        """
        return pt.forall_elim(var)


@register_macro("ereal_induct_macro")
class ErealInductMacro(InductMacro):
    """Induction macro for the ``ereal`` datatype.

    The induction theorem is expected to have the shape
    ``⊢ P(ereal_bot) ⟶ (∀r. P(ereal_real r)) ⟶ ∀z. P(z)``.
    """

    induct_th_name = "ereal_induct"
