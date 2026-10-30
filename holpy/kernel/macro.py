# Author: Bohua Zhan

"""Proof macros: derived proof methods with a trust level.

A macro is a named, reusable derivation step. When a proof is checked, the
kernel either evaluates the macro directly (for trusted levels) or expands it
into a proof term that is checked recursively. This module defines the common
interface; concrete macros live in ``holpy.logic``, ``holpy.data``, and the
application packages.
"""

from __future__ import annotations

from typing import Any, Sequence

from holpy.kernel.proof import ItemID, Proof
from holpy.kernel.proofterm import ProofTerm
from holpy.kernel.thm import Thm


class Macro:
    """Base class for a derived proof method.

    A single macro invocation may stand for many primitive derivation steps or
    nested macro calls. Macros reduce proof size and give higher layers a
    stable proof-method vocabulary.

    Attributes
    ----------
    level : int or None
        Trust level. A macro is evaluated directly when its level is less than
        or equal to the checker's ``check_level``; otherwise it is expanded.
    sig : object
        Argument signature used by the proof-state layer. Primitive-style
        macros use a term type; methods use a list of argument names.
    limit : str or None
        Optional theorem name that must be available before the macro may be
        used.
    """

    limit: str | None

    def __init__(self):
        self.level: int | None = None
        self.sig: object = None

    def eval(self, args: Any, prevs: list[Thm]) -> Thm:
        """Evaluate the macro and return the resulting theorem.

        Parameters
        ----------
        args : Any
            Argument of the proof method. Usually a Term, but some macros use
            a rule-specific tuple such as a theorem name and instantiation.
        prevs : list[Thm]
            Previously proved theorems consumed by the macro.

        Returns
        -------
        Thm
            The theorem produced by the macro.
        """
        pts = [ProofTerm.sorry(prev) for prev in prevs]
        return self.get_proof_term(args, pts).th

    def get_proof_term(self, args: Any, prevs: Sequence[ProofTerm]) -> ProofTerm:
        """Return a proof term expanding the macro.

        Subclasses must override this. ``prevs`` is a sequence of proof terms
        for the previously proved theorems; it may be a list or a tuple.
        """
        raise NotImplementedError("Proof term not implemented for %s" % type(self))

    def expand(self, prefix: ItemID, args: Any, prevs: list[tuple[ItemID, Thm]]) -> Proof:
        """Expand the macro into a linear proof under ``prefix``.

        Parameters
        ----------
        prefix : ItemID
            Identifier prefix for the generated proof lines.
        args : Any
            Argument of the proof method. Usually a Term, but some macros use
            a rule-specific tuple such as a theorem name and instantiation.
        prevs : list of (ItemID, Thm)
            Identifiers and statements of the previously proved theorems.

        Returns
        -------
        Proof
            The expanded linear proof.
        """
        pts = tuple([ProofTerm.atom(id, prev) for id, prev in prevs])
        return self.get_proof_term(args, pts).export(prefix)
