"""Kernel of holpy: the trusted higher-order logic core.

The kernel provides the datatypes for HOL types, terms, theorems, primitive
derivations, proofs, and theory state. It deliberately contains no parsing,
pretty-printing policy, or proof search: those live in ``holpy.syntax``,
``holpy.logic``, and the higher layers.

Every theorem produced by holpy is checked against the primitive derivations in
:mod:`holpy.kernel.thm`; this package is therefore the smallest and most
security-sensitive part of the codebase.
"""
