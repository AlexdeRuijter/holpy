# Author: Bohua Zhan

"""Utilities for creating fresh variable and constant names."""

from __future__ import annotations


def get_variant_name(nm: str, prevs: list[str]) -> str:
    """Return ``nm`` or the first numbered variant not present in ``prevs``."""
    if nm not in prevs:
        return nm

    i = 1
    while True:
        if nm + str(i) not in prevs:
            return nm + str(i)
        i += 1


def get_variant_names(nms: list[str], prevs: list[str]) -> list[str]:
    """Return fresh variants of ``nms`` that avoid all names in ``prevs``.

    Later names also avoid the variants chosen for earlier names.
    """
    if len(nms) == 0:
        return []
    nm = get_variant_name(nms[0], prevs)
    nm_rest = get_variant_names(nms[1:], prevs + [nm])
    return [nm] + nm_rest
