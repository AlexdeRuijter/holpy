"""Tests for the import-time behaviour of holpy.data.real.

Importing holpy.data.real must not load a theory: the theory loader imports
this module itself (see holpy.logic.basic.load_theory_cache), so a
module-level load would re-enter the loader.  The checks run in fresh
processes because an already imported module cannot be observed changing
theory.thy.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import textwrap
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]


def run_in_fresh_process(code: str) -> subprocess.CompletedProcess[str]:
    """Run Python code in a fresh process rooted at the repository.

    Parameters
    ----------
    code : str
        Python source passed to ``python -c``.

    Returns
    -------
    subprocess.CompletedProcess[str]
        The finished process, with stdout and stderr captured.

    """
    env = os.environ.copy()
    pythonpath = env.get('PYTHONPATH')
    env['PYTHONPATH'] = str(REPO_ROOT) + (os.pathsep + pythonpath if pythonpath else '')
    return subprocess.run(
        [sys.executable, '-c', textwrap.dedent(code)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )


class RealImportTest(unittest.TestCase):
    def assert_process_ok(self, proc: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(
            proc.returncode, 0,
            "fresh process failed:\nstdout:\n%s\nstderr:\n%s" % (proc.stdout, proc.stderr),
        )

    def testImportRealDoesNotChangeTheory(self) -> None:
        """Importing holpy.data.real neither replaces nor extends theory.thy."""
        proc = run_in_fresh_process(
            """
            from holpy.kernel import theory
            from holpy.logic import basic

            basic.load_theory('logic')
            before = theory.thy
            before_theorems = set(theory.thy.get_data('theorems'))

            from holpy.data import real

            assert theory.thy is before, "importing holpy.data.real replaced theory.thy"
            after_theorems = set(theory.thy.get_data('theorems'))
            assert after_theorems == before_theorems, (
                "importing holpy.data.real added theorems: %s"
                % sorted(after_theorems - before_theorems)
            )
            """
        )
        self.assert_process_ok(proc)

    def testImportRealIntoEmptyTheory(self) -> None:
        """With no theory loaded, importing holpy.data.real leaves theory.thy empty."""
        proc = run_in_fresh_process(
            """
            from holpy.kernel import theory

            assert theory.thy is None
            from holpy.data import real
            assert theory.thy is None, "importing holpy.data.real loaded a theory"
            """
        )
        self.assert_process_ok(proc)

    def testLoadRealInFreshProcess(self) -> None:
        """basic.load_theory('real') works without a prior import of the module."""
        proc = run_in_fresh_process(
            """
            from holpy.logic import basic

            basic.load_theory('real')
            """
        )
        self.assert_process_ok(proc)

    def testLoadRealAfterIntervalArithInFreshProcess(self) -> None:
        """Loading interval_arith first does not disturb a later load of real."""
        proc = run_in_fresh_process(
            """
            from holpy.logic import basic

            basic.load_theory('interval_arith')
            basic.load_theory('real')
            """
        )
        self.assert_process_ok(proc)


if __name__ == '__main__':
    unittest.main()
