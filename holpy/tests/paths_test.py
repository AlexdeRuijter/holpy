"""Tests for the theory search path in :mod:`holpy._paths`."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from holpy import _paths
from holpy._paths import add_theory_path, find_theory, library_dir, theory_path


class TheoryPathTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_env = os.environ.get("HOLPY_THEORY_PATH")
        self._saved_added = list(_paths._added_paths)
        self._saved_env_cache = _paths._env_path_cache
        self._saved_missing = set(_paths._missing_warned)
        self._saved_shadow = set(_paths._shadow_warned)
        self._saved_listeners = list(_paths._path_listeners)

        os.environ.pop("HOLPY_THEORY_PATH", None)
        _paths._added_paths.clear()
        _paths._env_path_cache = None
        _paths._missing_warned.clear()
        _paths._shadow_warned.clear()
        _paths._path_listeners.clear()

        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        if self._saved_env is None:
            os.environ.pop("HOLPY_THEORY_PATH", None)
        else:
            os.environ["HOLPY_THEORY_PATH"] = self._saved_env
        _paths._added_paths[:] = self._saved_added
        _paths._env_path_cache = self._saved_env_cache
        _paths._missing_warned.clear()
        _paths._missing_warned.update(self._saved_missing)
        _paths._shadow_warned.clear()
        _paths._shadow_warned.update(self._saved_shadow)
        _paths._path_listeners[:] = self._saved_listeners

    def make_dir(self, name: str) -> Path:
        directory = self.tmp / name
        directory.mkdir()
        return directory

    def test_environment_path_order_and_bundled_last(self) -> None:
        first = self.make_dir("first")
        second = self.make_dir("second")
        os.environ["HOLPY_THEORY_PATH"] = os.pathsep.join((str(first), str(second)))

        self.assertEqual(theory_path(), [first, second, library_dir()])

    def test_empty_and_missing_environment_entries_are_skipped(self) -> None:
        present = self.make_dir("present")
        missing = self.tmp / "missing"
        value = os.pathsep.join(("", str(present), "", str(missing), ""))
        os.environ["HOLPY_THEORY_PATH"] = value

        with self.assertLogs("holpy._paths", level="WARNING") as captured:
            self.assertEqual(theory_path(), [present, library_dir()])

        self.assertEqual(len(captured.records), 1)
        self.assertIn(str(missing), captured.records[0].getMessage())

        with mock.patch.object(_paths._logger, "warning") as warning:
            self.assertEqual(theory_path(), [present, library_dir()])
        warning.assert_not_called()

    def test_add_theory_path_prepend_and_append(self) -> None:
        first = self.make_dir("first")
        second = self.make_dir("second")
        third = self.make_dir("third")

        add_theory_path(first)
        add_theory_path(second)
        add_theory_path(third, prepend=False)

        self.assertEqual(
            theory_path(), [second, first, third, library_dir()]
        )

    def test_add_theory_path_is_idempotent(self) -> None:
        first = self.make_dir("first")
        calls: list[bool] = []
        _paths._path_listeners.append(lambda: calls.append(True))

        add_theory_path(first)
        add_theory_path(first)
        add_theory_path(first, prepend=False)

        self.assertEqual(theory_path(), [first, library_dir()])
        self.assertEqual(calls, [True])

    def test_add_theory_path_notifies_listeners(self) -> None:
        first = self.make_dir("first")
        calls: list[bool] = []
        _paths._path_listeners.append(lambda: calls.append(True))

        add_theory_path(first)

        self.assertEqual(calls, [True])

    def test_find_theory_prefers_temp_over_bundled(self) -> None:
        first = self.make_dir("first")
        theory_file = first / "nat.json"
        theory_file.write_text("{}", encoding="utf-8")
        os.environ["HOLPY_THEORY_PATH"] = str(first)

        # Shadowing warnings themselves are covered with the loader tests.
        with mock.patch.object(_paths._logger, "warning"):
            self.assertEqual(find_theory("nat"), theory_file)

    def test_find_theory_in_added_directory(self) -> None:
        first = self.make_dir("first")
        theory_file = first / "mythy.json"
        theory_file.write_text("{}", encoding="utf-8")
        add_theory_path(first)

        self.assertEqual(find_theory("mythy"), theory_file)

    def test_find_theory_unknown_raises(self) -> None:
        add_theory_path(self.make_dir("first"))

        with self.assertRaises(FileNotFoundError):
            find_theory("no_such_theory_abc")

    def test_no_path_uses_library_only(self) -> None:
        self.assertEqual(theory_path(), [library_dir()])


if __name__ == "__main__":
    unittest.main()
