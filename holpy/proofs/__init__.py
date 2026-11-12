"""Canonical theory JSON writer and proof-level operations."""

from holpy.proofs.jsonio import dumps_theory, write_theory
from holpy.proofs.levels import (
    Level,
    ProofContext,
    condense,
    condense_theory,
    expand,
    expand_theory,
    level_of,
    oracles,
)

__all__ = [
    "dumps_theory",
    "write_theory",
    "Level",
    "ProofContext",
    "expand",
    "condense",
    "level_of",
    "oracles",
    "expand_theory",
    "condense_theory",
]
