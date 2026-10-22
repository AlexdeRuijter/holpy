# Author: Bohua Zhan

"""Linear proof objects and editing primitives.

A proof is a list of :class:`ProofItem` entries. Each item stores a rule, its
arguments, the identifiers of previous items it consumes, and optionally the
statement it proves. Subproofs are attached to an item and share the same
identifier space through :class:`ItemID`.

The classes here are the mutable editing layer used by the proof-state
server. Logical checking itself lives in :mod:`holpy.kernel.theory`.
"""

from __future__ import annotations

import copy
from typing import Any, List, Optional, Tuple, Union

from holpy.kernel.term import Term, Inst
from holpy.kernel.thm import Thm


class ItemID:
    """Identifier of a proof item, stored as a tuple of integers.

    Accepted input forms are ``None`` (the empty identifier), a tuple of
    integers, a single integer, a dotted string such as ``"1.2.0"``, or
    another :class:`ItemID`.
    """

    id: tuple[int, ...]

    def __init__(self, id: Union[None, Tuple[int, ...], int, str, "ItemID"] = None):
        """Convert ``id`` into tuple form."""
        self.id: tuple[int, ...]
        if id is None:
            self.id = tuple()
        elif isinstance(id, tuple) and all(isinstance(i, int) for i in id):
            self.id = id
        elif isinstance(id, int):
            self.id = (id,)
        elif isinstance(id, str):
            self.id = tuple(int(s) for s in id.split("."))
        elif isinstance(id, ItemID):
            self.id = id.id
        else:
            raise TypeError

    def __str__(self) -> str:
        """Print the identifier in ``n1.n2.n3`` form."""
        return ".".join(str(i) for i in self.id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ItemID) and self.id == other.id

    def incr_id_after(self, start: "ItemID", n: int) -> "ItemID":
        """Adjust this identifier after inserting ``n`` lines before ``start``.

        Suppose ``start`` has length ``k``. Every identifier of length at least
        ``k`` whose first ``k - 1`` components agree with ``start`` and whose
        ``k``-th component is at least ``start``'s is shifted by ``n`` at that
        component; the remaining components are unchanged.
        """
        k = len(start.id)
        if len(self.id) >= k and self.id[:k-1] == start.id[:k-1] and self.id[k-1] >= start.id[k-1]:
            return ItemID(self.id[:k-1] + (self.id[k-1] + n,) + self.id[k:])
        else:
            return self

    def incr_id(self, n: int) -> "ItemID":
        """Increment the last component of the identifier by ``n``."""
        return ItemID(self.id[:-1] + (self.id[-1] + n,))

    def decr_id(self, id_remove: "ItemID") -> "ItemID":
        """Close the gap left by removing ``id_remove``.

        The logic is the inverse of :meth:`incr_id_after`: identifiers in the
        affected sibling range are shifted down by one at the component where
        the removed item lived.
        """
        k = len(id_remove.id)
        if len(self.id) >= k and self.id[:k-1] == id_remove.id[:k-1] and self.id[k-1] > id_remove.id[k-1]:
            return ItemID(self.id[:k-1] + (self.id[k-1] - 1,) + self.id[k:])
        else:
            return self

    def last(self) -> int:
        """Return the last component of the identifier."""
        return self.id[-1]

    def can_depend_on(self, other: "ItemID") -> bool:
        """Return whether this item may depend on ``other``.

        A dependency is legal only when ``other`` is in the same proof or an
        enclosing subproof and appears earlier in the linear order.
        """
        l = len(other.id)
        if l > len(self.id):
            return False
        if other.id[:l-1] != self.id[:l-1]:
            return False
        return other.id[l-1] < self.id[l-1]


class ProofStateException(Exception):
    """Raised when a requested proof item or subproof does not exist."""


class ProofItem:
    """One line of a proof.

    Attributes
    ----------
    id : ItemID
        Identifier used by later items.
    rule : str
        Primitive derivation or macro name.
    args : object
        Arguments to the rule.
    prevs : list of ItemID
        Previous items consumed by this rule.
    th : Thm or None
        Optional expected statement.
    subproof : Proof or None
        Optional expanded subproof.
    """

    def __init__(self, id, rule: str, *, args: Any = None,
                 prevs: list[ItemID | tuple[int, ...] | int | str] | None = None,
                 th: Thm | None = None):
        self.id: ItemID = ItemID(id)
        self.rule: str = rule
        self.args = args
        self.prevs: List[ItemID] = [ItemID(prev) for prev in prevs] if prevs is not None else []
        self.th: Optional[Thm] = th
        self.subproof: Optional[Proof] = None

    def print_str_args(self) -> str:
        """Render this item's arguments for the textual proof view."""
        def str_val(val):
            if isinstance(val, Inst):
                items = sorted(val.items(), key=lambda pair: pair[0])
                return "{" + ", ".join(key + ": " + str_val(val) for key, val in items) + "}"
            else:
                return str(val)

        if isinstance(self.args, tuple):
            return ", ".join(str_val(val) for val in self.args)
        elif self.args:
            return str_val(self.args)
        else:
            return ""

    def __str__(self) -> str:
        """Print the proof item."""
        str_id = str(self.id)
        str_args = " " + self.print_str_args() if self.args else ""
        str_prevs = " from " + ", ".join(str(prev) for prev in self.prevs) if self.prevs else ""
        str_th = str(self.th) + " by " if self.th else ""
        cur_line = str_id + ": " + str_th + self.rule + str_args + str_prevs
        if self.subproof:
            return cur_line + "\n" + "\n".join(str(item) for item in self.subproof.items)
        else:
            return cur_line

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ProofItem) and self.id == other.id and self.rule == other.rule and \
            self.args == other.args and self.prevs == other.prevs and self.th == other.th

    def __copy__(self) -> "ProofItem":
        res = ProofItem(self.id, self.rule, args=self.args, prevs=self.prevs, th=self.th)
        if self.subproof:
            res.subproof = copy.copy(self.subproof)
        return res

    def get_sorrys(self) -> List[Thm]:
        """Return the gaps in this item, including those in subproofs."""
        if self.rule == 'sorry':
            assert self.subproof is None
            return [self.th]

        if self.subproof:
            return sum([item.get_sorrys() for item in self.subproof.items], [])
        else:
            return []

    def incr_proof_item(self, start: ItemID, n: int):
        """Shift all identifiers in this item and its subproofs."""
        self.id = self.id.incr_id_after(start, n)
        self.prevs = [id.incr_id_after(start, n) for id in self.prevs]
        if self.subproof:
            for subitem in self.subproof.items:
                subitem.incr_proof_item(start, n)

    def decr_proof_item(self, id_remove: ItemID):
        """Close the identifier gap left by ``id_remove`` in this item."""
        self.id = self.id.decr_id(id_remove)
        self.prevs = [id.decr_id(id_remove) for id in self.prevs]
        if self.subproof:
            for subitem in self.subproof.items:
                subitem.decr_proof_item(id_remove)


class Proof:
    """A linear proof in natural-deduction form.

    Each item derives a theorem from zero or more previous items. Subproofs
    own their own item lists but use the same :class:`ItemID` namespace.
    """

    def __init__(self, *assums: Term):
        """Initialize with zero or more assumptions.

        The first ``n`` items are ``0, ..., n - 1``, each introduced by
        ``Thm.assume`` on the corresponding assumption.
        """
        self.items: List[ProofItem] = [ProofItem(i, "assume", args=assum)
                                       for i, assum in enumerate(assums)]

    def add_item(self, id, rule: str, *, args: Any = None,
                 prevs: list[ItemID | tuple[int, ...] | int | str] | None = None,
                 th: Thm | None = None):
        """Append an item to the proof."""
        if prevs is None:
            prevs = []
        self.items.append(ProofItem(id, rule, args=args, prevs=prevs, th=th))

    def __str__(self) -> str:
        """Print the proof line by line."""
        return '\n'.join(str(item) for item in self.items)

    def __repr__(self) -> str:
        return str(self)

    def __copy__(self) -> "Proof":
        res = Proof()
        res.items = [copy.copy(item) for item in self.items]
        return res

    def find_item(self, id: ItemID) -> ProofItem:
        """Find the item at ``id``.

        Raises
        ------
        ProofStateException
            If the path does not resolve to an item.
        """
        try:
            item = self.items[id.id[0]]
            for i in id.id[1:]:
                item = item.subproof.items[i]
            return item
        except (AttributeError, IndexError):
            raise ProofStateException

    def get_parent_proof(self, id: ItemID) -> "Proof":
        """Return the subproof containing ``id``.

        Raises
        ------
        ProofStateException
            If the subproof path does not exist.
        """
        try:
            prf = self
            for i in id.id[:-1]:
                prf = prf.items[i].subproof
            if prf is None:
                raise ProofStateException
            return prf
        except IndexError:
            raise ProofStateException

    def insert_item(self, item: ProofItem):
        """Insert ``item`` at the end of the subproof selected by its id.

        The item's id must point exactly one past the current last line of
        that subproof.
        """
        try:
            prf = self
            for i in item.id.id[:-1]:
                if prf.items[i].subproof is None:
                    prf.items[i].subproof = Proof()
                prf = prf.items[i].subproof
            if item.id.id[-1] != len(prf.items):
                raise ProofStateException
            prf.items.append(item)
        except IndexError:
            raise ProofStateException

    def get_sorrys(self) -> List[Thm]:
        """Return all gaps in the proof."""
        return sum([item.get_sorrys() for item in self.items], [])
