# Author: Bohua Zhan

"""Union-find with path compression and union by size."""

from __future__ import annotations

from typing import Any


class UnionFind:
    """Disjoint-set forest over arbitrary hashable items.

    Attributes
    ----------
    parents : dict
        Map from an item to its parent; roots map to ``None``.
    size : dict
        Map from an item to its subtree size; non-roots use ``None``.
    """

    def __init__(self):
        """Initialize an empty union-find data structure."""
        # Map from node to parent of that node. If the node is the root,
        # the value is None.
        self.parents: dict[Any, Any] = dict()

        # Map from node to size of subtree based at that node.
        self.size: dict[Any, int | None] = dict()

    def __str__(self) -> str:
        res = ""
        for k, v in self.parents.items():
            res += str(k) + ": " + str(v) + "\n"
        return res

    def has_key(self, item: Any) -> bool:
        """Return whether ``item`` is present in the structure."""
        return item in self.parents

    def insert(self, item: Any):
        """Insert a new singleton class containing ``item``."""
        assert item not in self.parents, "insert: item already in union-find."

        self.parents[item] = None
        self.size[item] = 1

    def find(self, item: Any) -> Any:
        """Return the representative of ``item``, compressing the path."""
        assert item in self.parents, "find: item not in union-find."

        path = []
        while self.parents[item] is not None:
            path.append(item)
            item = self.parents[item]

        for i in path:
            self.parents[i] = item

        return item

    def union(self, item1: Any, item2: Any, force_first: bool = False):
        """Join the classes containing the two items.

        Parameters
        ----------
        item1, item2 : Any
            Items whose classes are merged.
        force_first : bool
            If true, ``item1``'s root remains the root even when the other
            tree is larger.
        """
        item1 = self.find(item1)
        item2 = self.find(item2)

        # Ensure the tree at item1 is larger or equal to tree at item2.
        if not force_first and self.size[item1] < self.size[item2]:
            item1, item2 = item2, item1

        self.parents[item2] = item1
        self.size[item1] += self.size[item2]
        self.size[item2] = None
