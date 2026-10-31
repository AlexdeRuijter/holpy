# Author: Bohua Zhan

"""Proof-checking and theory-extension reports.

These objects are diagnostics: they count primitive steps, record which
theorems and macros were used, and collect gaps or axioms. They never
participate in the logical derivation itself.
"""

from __future__ import annotations

from holpy.kernel.thm import Thm
from holpy.kernel.type import Type


class ProofReport:
    """Accumulated statistics for checking one proof.

    Attributes
    ----------
    steps : int
        Total checked steps: theorem applications, primitive derivations, and
        evaluated macro invocations each count as one step. Expanded macros are
        counted through their expansion, not as an extra step.
    thm_steps : int
        Number of invocations of existing theorems.
    prim_steps : int
        Number of primitive-derivation invocations.
    macro_steps : int
        Number of evaluated macro invocations.
    th_names : set of str
        Names of theorems used.
    macros_eval : set of str
        Names of macros evaluated directly.
    macros_expand : set of str
        Names of macros expanded into primitive steps.
    gaps : list of Thm
        Statements accepted as gaps (``sorry``).
    """

    def __init__(self):
        self.steps = 0
        self.thm_steps = 0
        self.prim_steps = 0
        self.macro_steps = 0
        self.th_names: set[str] = set()
        self.macros_eval: set[str] = set()
        self.macros_expand: set[str] = set()
        self.gaps: list[Thm] = []

    def __str__(self) -> str:
        return "\n".join([
            "Steps: " + str(self.steps),
            "  Theorems:  " + str(self.thm_steps),
            "  Primitive: " + str(self.prim_steps),
            "  Macro:     " + str(self.macro_steps),
            "Theorems applied: " + ", ".join(self.th_names),
            "Macros evaluated: " + ", ".join(self.macros_eval),
            "Macros expanded: " + ", ".join(self.macros_expand),
            "Gaps: " + str(self.gaps)])

    def __repr__(self) -> str:
        return str(self)

    def json_data(self) -> dict:
        """Return the report as a JSON-serializable dictionary."""
        return {
            "steps": self.steps,
            "thm_steps": self.thm_steps,
            "prim_steps": self.prim_steps,
            "macro_steps": self.macro_steps,
            "th_names": sorted(list(self.th_names)),
            "macros_eval": sorted(list(self.macros_eval)),
            "macros_expand": sorted(list(self.macros_expand)),
            "num_gaps": len(self.gaps)
        }

    def apply_theorem(self, th_name: str):
        """Record an application of an existing theorem."""
        self.steps += 1
        self.thm_steps += 1
        self.th_names.add(th_name)

    def apply_primitive_deriv(self):
        """Record an application of a primitive derivation."""
        self.steps += 1
        self.prim_steps += 1

    def eval_macro(self, macro_name: str):
        """Record a macro that was evaluated without expansion."""
        self.steps += 1
        self.macro_steps += 1
        self.macros_eval.add(macro_name)

    def expand_macro(self, macro_name: str):
        """Record a macro that was expanded into primitive steps."""
        self.macros_expand.add(macro_name)

    def add_gap(self, th: Thm):
        """Register a gap with statement ``th``."""
        self.gaps.append(th)

    def steps_stat(self) -> tuple[int, int, int]:
        """Return ``(thm_steps, prim_steps, macro_steps)``."""
        return (self.thm_steps, self.prim_steps, self.macro_steps)


class ExtensionReport:
    """Report of the axioms introduced by a checked theory extension.

    Attributes
    ----------
    axioms : list of tuple
        Each entry is ``(name, info)`` where ``info`` is an arity, a type, or
        a theorem statement.
    """

    def __init__(self):
        self.axioms: list[tuple[str, int | Type | Thm]] = []

    def add_axiom(self, name: str, info: int | Type | Thm):
        """Record an axiomatic extension."""
        self.axioms.append((name, info))

    def get_axioms(self) -> list[tuple[str, int | Type | Thm]]:
        """Return the recorded axioms."""
        return self.axioms

    def __str__(self) -> str:
        def print_axiom(axiom: tuple[str, int | Type | Thm]) -> str:
            (name, info) = axiom
            if isinstance(info, int):
                return "Type " + name + " with arity " + str(info)
            elif isinstance(info, Type):
                return name + " :: " + str(info)
            elif isinstance(info, Thm):
                return name + ": " + str(info)
            else:
                raise TypeError

        return "Axiom added: %s\n%s" % (
            len(self.axioms), '\n'.join(print_axiom(axiom) for axiom in self.axioms))
