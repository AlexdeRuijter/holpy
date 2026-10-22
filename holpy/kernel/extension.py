# Author: Bohua Zhan

"""Theory extensions and their JSON-facing representation.

An :class:`Extension` is one atomic addition to a theory: a type constructor,
a constant, a theorem, a theorem attribute, or an overload registration.
Extensions are collected by :mod:`holpy.kernel.theory` and are checked there
before they become part of the current theory.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from holpy.kernel.thm import Thm
from holpy.kernel.type import Type

if TYPE_CHECKING:  # imported for annotations only; avoids a kernel import cycle
    from holpy.kernel.proof import Proof


class Extension:
    """Base class for an atomic theory extension.

    The concrete subclasses are :class:`TConst`, :class:`Constant`,
    :class:`Theorem`, :class:`Attribute`, and :class:`Overload`.
    """

    # Values used by ``ty`` to distinguish extension kinds.
    TCONST, CONSTANT, THEOREM, ATTRIBUTE, OVERLOAD = range(5)

    ty: int
    name: str
    arity: int
    T: Type
    ref_name: str
    th: Thm
    prf: object
    attribute: str

    def is_tconst(self) -> bool:
        """Return whether this is a type-constructor extension."""
        return self.ty == Extension.TCONST

    def is_constant(self) -> bool:
        """Return whether this is a constant extension."""
        return self.ty == Extension.CONSTANT

    def is_theorem(self) -> bool:
        """Return whether this is a theorem extension."""
        return self.ty == Extension.THEOREM

    def is_attribute(self) -> bool:
        """Return whether this is a theorem-attribute extension."""
        return self.ty == Extension.ATTRIBUTE

    def is_overload(self) -> bool:
        """Return whether this is an overload registration."""
        return self.ty == Extension.OVERLOAD

    def __str__(self) -> str:
        if self.ty == Extension.TCONST:
            return "Type " + self.name + " " + str(self.arity)
        elif self.ty == Extension.CONSTANT:
            ref_str = " (" + self.ref_name + ")" if self.ref_name != self.name else ""
            return "Constant " + self.name + " :: " + str(self.T) + ref_str
        elif self.ty == Extension.THEOREM:
            return "Theorem " + self.name + ": " + str(self.th)
        elif self.ty == Extension.ATTRIBUTE:
            return "Attribute " + self.name + " [" + self.attribute + "]"
        elif self.ty == Extension.OVERLOAD:
            return "Overload " + self.name
        else:
            raise TypeError

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: Extension) -> bool:
        if self.ty != other.ty:
            return False
        elif self.ty == Extension.TCONST:
            return self.name == other.name and self.arity == other.arity
        elif self.ty == Extension.CONSTANT:
            return self.name == other.name and self.T == other.T
        elif self.ty == Extension.THEOREM:
            return self.name == other.name and self.th == other.th and self.prf == other.prf
        elif self.ty == Extension.ATTRIBUTE:
            return self.name == other.name and self.attribute == other.attribute
        elif self.ty == Extension.OVERLOAD:
            return self.name == other.name
        else:
            raise TypeError


class TConst(Extension):
    """Extension adding a type constructor."""

    def __init__(self, name: str, arity: int):
        """Create a type-constructor extension.

        Parameters
        ----------
        name : str
            Name of the type constructor.
        arity : int
            Number of type arguments accepted by the constructor.
        """
        self.ty = Extension.TCONST
        self.name = name
        self.arity = arity


class Constant(Extension):
    """Extension adding a term constant."""

    def __init__(self, name: str, T: Type, *, ref_name: str | None = None):
        """Create a constant extension.

        Parameters
        ----------
        name : str
            Name of the constant.
        T : Type
            Most general type of the constant.
        ref_name : str, optional
            Name used when printing the constant; defaults to ``name``.
        """
        self.ty = Extension.CONSTANT
        self.name = name
        self.T = T
        self.ref_name = name if ref_name is None else ref_name


class Theorem(Extension):
    """Extension adding an axiom or a proved theorem."""

    def __init__(self, name: str, th: Thm, prf: Proof | None = None):
        """Create a theorem extension.

        Parameters
        ----------
        name : str
            Name of the theorem.
        th : Thm
            Statement of the theorem.
        prf : Proof, optional
            Proof of the theorem. ``None`` makes this an axiomatic extension.
        """
        self.ty = Extension.THEOREM
        self.name = name
        self.th = th
        self.prf = prf


class Attribute(Extension):
    """Extension attaching an attribute to a theorem."""

    def __init__(self, name: str, attribute: str):
        """Create an attribute extension.

        Parameters
        ----------
        name : str
            Name of the theorem receiving the attribute.
        attribute : str
            Attribute name.
        """
        self.ty = Extension.ATTRIBUTE
        self.name = name
        self.attribute = attribute


class Overload(Extension):
    """Extension registering an overloaded constant name."""

    def __init__(self, name: str):
        """Create an overload extension.

        Parameters
        ----------
        name : str
            Base name of the overloaded constant.
        """
        self.ty = Extension.OVERLOAD
        self.name = name
