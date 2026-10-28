# macros/__init__.py
#
# induct is registered on import (holpy.logic.logic imports it).
# linarith depends on holpy.data and is registered when the real theory is
# loaded (see holpy.logic.basic.load_theory_cache).
from . import induct  # noqa: F401  (registers the macro)
from . import structural  # noqa: F401  (registers exI_list, conj_*, contr, cases)
from . import semiring  # noqa: F401  (registers semiring_norm)
