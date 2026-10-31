#!/usr/bin/env python
"""Compare the ASTs of two git revisions while ignoring documentation.

The script is a review aid for style-only changes: it parses every Python file
under ``PATH`` at ``BASE`` and ``HEAD``, removes docstrings (and optionally all
annotations), and compares the resulting :func:`ast.dump` output.  It prints
the files whose code differs and exits with status 1 when any differ.

Usage, from anywhere inside the repository::

    python scripts/ast_diff.py BASE HEAD PATH [--ignore-annotations]

``PATH`` is a file or directory relative to the repository root.  ``BASE`` and
``HEAD`` are any git refs; the special ref ``WORKTREE`` reads the current
working tree from disk instead.

Docstrings are the first string-expression statement of a module, class, or
function.  With ``--ignore-annotations`` the script also drops return
annotations, argument annotations, the annotation of an ``AnnAssign``
(``x: int = 1`` is compared as ``x = 1``), annotation-only declarations
(``x: int`` with no value), and imports from :mod:`typing`.
"""

from __future__ import annotations

import argparse
import ast
import logging
import subprocess
import sys
from pathlib import Path
from typing import Iterable

logger = logging.getLogger("ast_diff")

WORKTREE = "WORKTREE"


def _repo_root() -> Path:
    """Return the root of the git work tree containing the current directory."""
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("not inside a git repository")
    return Path(result.stdout.strip())


def _normalize_path(value: str, root: Path) -> str:
    """Return ``value`` as a repository-relative POSIX path.

    Parameters
    ----------
    value : str
        User-supplied path, relative to the repository root or absolute.
    root : Path
        Repository root.

    Returns
    -------
    str
        Normalized path relative to ``root``.
    """
    path = Path(value)
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise ValueError("PATH must be inside the repository") from exc
    return path.as_posix() if str(path) else "."


def _run_git(args: Iterable[str], root: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command in ``root`` and return the completed process."""
    return subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _list_ref_files(ref: str, path: str, root: Path) -> list[str]:
    """List the Python files under ``path`` at git revision ``ref``."""
    result = _run_git(["ls-tree", "-r", "--name-only", ref, path], root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return sorted(
        name for name in result.stdout.splitlines()
        if name.endswith(".py")
    )


def _list_worktree_files(path: str, root: Path) -> list[str]:
    """List the Python files under ``path`` in the working tree."""
    target = root / path
    if target.is_file():
        return [path] if target.suffix == ".py" else []
    if not target.is_dir():
        return []

    files = []
    for candidate in target.rglob("*.py"):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(root)
        if ".git" in relative.parts:
            continue
        files.append(relative.as_posix())
    return sorted(files)


def _read_source(ref: str, path: str, root: Path) -> str:
    """Return the text of ``path`` at ``ref`` (or from the working tree)."""
    if ref == WORKTREE:
        return (root / path).read_text(encoding="utf-8")

    result = _run_git(["show", f"{ref}:{path}"], root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())
    return result.stdout


def _is_docstring_statement(node: ast.stmt) -> bool:
    """Return whether ``node`` is a plain string-expression statement."""
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


class _DocstringStripper(ast.NodeTransformer):
    """Remove the first docstring from every module, class, and function."""

    def _strip(self, node: ast.Module | ast.ClassDef | ast.FunctionDef
               | ast.AsyncFunctionDef) -> ast.AST:
        if node.body and _is_docstring_statement(node.body[0]):
            del node.body[0]
        return self.generic_visit(node)

    def visit_Module(self, node: ast.Module) -> ast.AST:
        return self._strip(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        return self._strip(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._strip(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._strip(node)


class _AnnotationStripper(ast.NodeTransformer):
    """Remove annotations from arguments, returns, and annotated assignments.

    Imports from :mod:`typing` are also removed: they exist only to support
    annotations in the files this script compares, and keeping them would make
    an otherwise annotation-only change look like a code change.
    """

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST | None:
        if node.module == "typing":
            return None
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.annotation = None
        if hasattr(node, "type_comment"):
            node.type_comment = None
        return node

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
        node.returns = None
        if hasattr(node, "type_comment"):
            node.type_comment = None
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._visit_function(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> ast.AST | None:
        self.generic_visit(node)
        if node.value is None:
            # ``x: int`` is a declaration used only by type checkers.
            return None
        replacement = ast.Assign(
            targets=[node.target],
            value=node.value,
            type_comment=getattr(node, "type_comment", None),
        )
        return ast.copy_location(replacement, node)


def _normalized_dump(source: str, path: str, ignore_annotations: bool) -> str:
    """Parse ``source`` and return a dump without docstrings or annotations."""
    tree = ast.parse(source, filename=path)
    tree = _DocstringStripper().visit(tree)
    if ignore_annotations:
        tree = _AnnotationStripper().visit(tree)
        ast.fix_missing_locations(tree)
    return ast.dump(tree)


def main(argv: list[str] | None = None) -> int:
    """Run the AST comparison and return a process exit status."""
    parser = argparse.ArgumentParser(
        description="Print Python files whose code differs between two git refs.",
    )
    parser.add_argument("base", help="base git ref, or WORKTREE")
    parser.add_argument("head", help="head git ref, or WORKTREE")
    parser.add_argument(
        "path",
        help="file or directory under the repository root",
    )
    parser.add_argument(
        "--ignore-annotations",
        action="store_true",
        help="also ignore argument, return, and AnnAssign annotations",
    )
    args = parser.parse_args(argv)

    try:
        root = _repo_root()
        path = _normalize_path(args.path, root)
        if args.base == WORKTREE:
            base_files = set(_list_worktree_files(path, root))
        else:
            base_files = set(_list_ref_files(args.base, path, root))
        if args.head == WORKTREE:
            head_files = set(_list_worktree_files(path, root))
        else:
            head_files = set(_list_ref_files(args.head, path, root))
    except (RuntimeError, ValueError) as exc:
        logger.error("%s", exc)
        return 2

    differing = 0
    for name in sorted(base_files | head_files):
        if name not in base_files:
            print(f"added: {name}")
            differing += 1
            continue
        if name not in head_files:
            print(f"removed: {name}")
            differing += 1
            continue

        try:
            base_dump = _normalized_dump(
                _read_source(args.base, name, root),
                name,
                args.ignore_annotations,
            )
            head_dump = _normalized_dump(
                _read_source(args.head, name, root),
                name,
                args.ignore_annotations,
            )
        except (RuntimeError, OSError, SyntaxError) as exc:
            logger.error("%s: %s", name, exc)
            differing += 1
            continue

        if base_dump != head_dump:
            print(f"changed: {name}")
            differing += 1

    return 1 if differing else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    sys.exit(main())
