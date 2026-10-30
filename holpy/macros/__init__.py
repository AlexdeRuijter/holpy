"""Proof macros of HolPy.

Importing this package registers the macros of ``induct``, ``structural``,
``semiring`` and ``transfer``. ``induct`` is also registered when
``holpy.logic.logic`` is imported. ``linarith`` depends on ``holpy.data`` and
is not imported here: it is registered when the real theory is loaded (see
``holpy.logic.basic.load_theory_cache``).
"""

from holpy.macros import induct  # noqa: F401  (registers the macro)
from holpy.macros import structural  # noqa: F401  (registers exI_list, conj_*, contr, cases)
from holpy.macros import semiring  # noqa: F401  (registers semiring_norm)
from holpy.macros import transfer  # noqa: F401  (registers transfer)
