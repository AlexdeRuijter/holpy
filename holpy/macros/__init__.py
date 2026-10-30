"""Module docstring for holpy/macros.

Registers and exports the macro modules induct, structural, semiring,
transfer, and (through theory loading) linarith.
"""
from holpy.macros import induct  # noqa: F401  (registers the macro)
from holpy.macros import structural  # noqa: F401  (registers exI_list, conj_*, contr, cases)
from holpy.macros import semiring  # noqa: F401  (registers semiring_norm)
from holpy.macros import transfer  # noqa: F401  (registers transfer)
