"""Tests for theory path integration in basic loader."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from holpy import _paths
from holpy.logic import basic
from holpy.kernel.theory import TheoryException


class BasicPathTest(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_env = os.environ.get("HOLPY_THEORY_PATH")
        self._saved_added = list(_paths._added_paths)
        self._saved_env_cache = _paths._env_path_cache
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
        basic.theory_cache.clear()
        basic.item_index.clear()

    def test_load_mythy_imports_nat(self) -> None:
        dir_path = self.tmp / "mydir"
        dir_path.mkdir()
        mythy = dir_path / "mythy.json"
        mythy.write_text('{"name":"mythy","imports":["nat"],"description":"test","content":[]}', encoding="utf-8")
        os.environ["HOLPY_THEORY_PATH"] = str(dir_path)
        basic.load_theory("mythy")
        from holpy.kernel import theory
        self.assertTrue(theory.thy.has_theorem("add_0_right"))

    def test_add_theory_path_after_load(self) -> None:
        dir_path = self.tmp / "new"
        dir_path.mkdir()
        new_thy = dir_path / "newthy.json"
        new_thy.write_text('{"name":"newthy","imports":[],"description":"","content":[]}', encoding="utf-8")
        _paths.add_theory_path(str(dir_path))
        basic.load_theory("newthy")
        self.assertIn("newthy", basic.theory_cache.get("master", {}))

    def test_shadow_nat_warning(self) -> None:
        dir_path = self.tmp / "shadow"
        dir_path.mkdir()
        nat_path = dir_path / "nat.json"
        nat_path.write_text('{"name":"nat","imports":[],"description":"shadow","content":[]}', encoding="utf-8")
        os.environ["HOLPY_THEORY_PATH"] = str(dir_path)
        import logging
        with self.assertLogs("holpy._paths", level="WARNING") as cm:
            basic.load_metadata()
        self.assertTrue(any("shadowed" in str(r.message) for r in cm.records))

    def test_cycle_across_dirs_raises(self) -> None:
        dir1 = self.tmp / "d1"
        dir2 = self.tmp / "d2"
        dir1.mkdir()
        dir2.mkdir()
        (dir1 / "a.json").write_text('{"name":"a","imports":["b"],"description":"","content":[]}', encoding="utf-8")
        (dir2 / "b.json").write_text('{"name":"b","imports":["a"],"description":"","content":[]}', encoding="utf-8")
        os.environ["HOLPY_THEORY_PATH"] = os.pathsep.join([str(dir1), str(dir2)])
        with self.assertRaises(TheoryException):
            basic.load_metadata()

    def test_no_path_is_library_only(self) -> None:
        os.environ.pop("HOLPY_THEORY_PATH", None)
        _paths._added_paths.clear()
        self.assertEqual(_paths.theory_path(), [_paths.library_dir()])


if __name__ == "__main__":
    unittest.main()
