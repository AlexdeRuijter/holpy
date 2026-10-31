"""Tests for scripts/ast_diff.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ast_diff.py"


class AstDiffTest(unittest.TestCase):
    """Exercise the AST comparison through its command-line interface."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "ast-diff-test@example.com")
        self.git("config", "user.name", "AST Diff Test")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a git command in the temporary repository."""
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )

    def write(self, name: str, content: str) -> None:
        """Write a file in the temporary repository."""
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, message: str) -> str:
        """Commit all changes and return the new commit hash."""
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run ast_diff.py in the temporary repository."""
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_identical_file_reports_nothing(self) -> None:
        """Comparing a file with itself exits 0 and prints no file."""
        self.write("a.py", "def f(x):\n    return x\n")
        base = self.commit("base")

        result = self.run_script(base, base, "a.py")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_docstring_only_change_is_ignored(self) -> None:
        """A changed docstring does not count as a code change."""
        self.write("a.py", 'def f():\n    """old"""\n    return 1\n')
        base = self.commit("base")
        self.write("a.py", 'def f():\n    """new\n    text"""\n    return 1\n')
        head = self.commit("docstring")

        result = self.run_script(base, head, "a.py")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_code_change_is_reported(self) -> None:
        """A changed return value exits 1 and names the file."""
        self.write("a.py", "def f():\n    return 1\n")
        base = self.commit("base")
        self.write("a.py", "def f():\n    return 2\n")
        head = self.commit("code")

        result = self.run_script(base, head, "a.py")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("a.py", result.stdout)

    def test_annotation_only_change_requires_flag(self) -> None:
        """Annotations differ by default but are ignored with the flag."""
        self.write(
            "a.py",
            "def f(x):\n"
            '    """doc"""\n'
            "    y = 1\n"
            "    return x + y\n",
        )
        base = self.commit("base")
        self.write(
            "a.py",
            "def f(x: int) -> int:\n"
            '    """doc"""\n'
            "    y: int = 1\n"
            "    return x + y\n",
        )
        head = self.commit("annotations")

        without_flag = self.run_script(base, head, "a.py")
        with_flag = self.run_script(base, head, "a.py", "--ignore-annotations")

        self.assertEqual(without_flag.returncode, 1, without_flag.stderr)
        self.assertIn("a.py", without_flag.stdout)
        self.assertEqual(with_flag.returncode, 0, with_flag.stderr)
        self.assertEqual(with_flag.stdout, "")

    def test_annotation_imports_and_declarations_are_ignored(self) -> None:
        """typing imports and value-less declarations are annotation-only."""
        self.write(
            "a.py",
            "from typing import Any\n"
            "\n"
            "class C:\n"
            "    x = 1\n",
        )
        base = self.commit("base")
        self.write(
            "a.py",
            "from typing import Any, Sequence\n"
            "\n"
            "class C:\n"
            "    x: int = 1\n"
            "    y: Sequence[int]\n",
        )
        head = self.commit("annotations")

        without_flag = self.run_script(base, head, "a.py")
        with_flag = self.run_script(base, head, "a.py", "--ignore-annotations")

        self.assertEqual(without_flag.returncode, 1, without_flag.stderr)
        self.assertEqual(with_flag.returncode, 0, with_flag.stderr)
        self.assertEqual(with_flag.stdout, "")

    def test_added_file_is_reported(self) -> None:
        """A Python file present only at HEAD is reported as added."""
        self.write("a.py", "x = 1\n")
        base = self.commit("base")
        self.write("pkg/b.py", "y = 2\n")
        head = self.commit("add file")

        result = self.run_script(base, head, "pkg")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("added: pkg/b.py", result.stdout)

    def test_removed_file_is_reported(self) -> None:
        """A Python file present only at BASE is reported as removed."""
        self.write("a.py", "x = 1\n")
        self.write("pkg/b.py", "y = 2\n")
        base = self.commit("base")
        (self.root / "pkg" / "b.py").unlink()
        head = self.commit("remove file")

        result = self.run_script(base, head, "pkg")

        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn("removed: pkg/b.py", result.stdout)

    def test_worktree_ref_reads_disk(self) -> None:
        """WORKTREE compares against uncommitted files on disk."""
        self.write("a.py", 'def f():\n    """old"""\n    return 1\n')
        base = self.commit("base")

        self.write("a.py", 'def f():\n    """new"""\n    return 1\n')
        docstring = self.run_script(base, "WORKTREE", "a.py")
        self.assertEqual(docstring.returncode, 0, docstring.stderr)

        self.write("a.py", 'def f():\n    """new"""\n    return 2\n')
        code = self.run_script(base, "WORKTREE", "a.py")
        self.assertEqual(code.returncode, 1, code.stderr)
        self.assertIn("a.py", code.stdout)


if __name__ == "__main__":
    unittest.main()
