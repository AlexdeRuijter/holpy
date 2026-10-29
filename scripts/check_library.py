#!/usr/bin/env python
"""Check the stored proofs in the bundled holpy library.

The script replays each theorem's stored ``proof`` certificate, records the
outcome in a deterministic TSV file, and can compare two such files.  It is a
development tool: checking a whole theory can take minutes, and checking the
whole library takes hours.

Usage, from the repository root::

    python scripts/check_library.py [THEORY ...] [--out FILE] [--jobs N]
    python scripts/check_library.py --compare OLD.tsv NEW.tsv
"""

from __future__ import annotations

import argparse
import copy
import logging
import multiprocessing
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

# Running ``python scripts/check_library.py`` puts ``scripts/`` on sys.path,
# not the repository root, so make the checkout importable without relying on
# the caller's PYTHONPATH.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from holpy._paths import library_dir  # noqa: E402
from holpy.kernel import report as proof_report  # noqa: E402
from holpy.kernel import theory  # noqa: E402
from holpy.logic import basic, context  # noqa: E402
from holpy.server import items, server  # noqa: E402
from holpy.syntax import printer  # noqa: E402
from holpy.syntax.settings import global_setting  # noqa: E402

logger = logging.getLogger("check_library")

COLUMNS = (
    "theory",
    "name",
    "status",
    "error_type",
    "statement",
    "steps",
    "macros_eval",
    "time",
)
COMPARE_COLUMNS = ("status", "statement", "steps")


@dataclass(frozen=True)
class Row:
    """One theorem's result in the library check.

    Parameters
    ----------
    theory : str
        Name of the theory containing the theorem.
    item : int
        Index of the theorem item in the theory's JSON content.  This is kept
        out of the TSV and is used to preserve JSON item order in the output.
    name : str
        Theorem name.
    status : str
        ``ok`` when the proof checks and contains no ``sorry`` lines;
        ``gaps`` when it checks and contains at least one ``sorry`` line;
        ``fail`` when the check raises; ``noproof`` when there is no
        stored proof.
    error_type : str
        Exception class name for a failed proof, otherwise an empty string.
    statement : str
        The theorem statement as rendered by the printer.
    steps : int
        Kernel step count from the proof report, or zero without a proof.
    macros_eval : str
        Sorted comma-separated macro names evaluated during checking.
    time : float
        Wall-clock checking time in seconds, rounded to two decimals.
    """

    theory: str
    item: int
    name: str
    status: str
    error_type: str
    statement: str
    steps: int
    macros_eval: str
    time: float


def _escape_field(value: str) -> str:
    """Escape a TSV field so tabs and newlines cannot break the format.

    Parameters
    ----------
    value : str
        Raw field value.

    Returns
    -------
    str
        A single-line value with backslashes, tabs and newlines escaped.
    """
    return (
        value.replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def _printed_statement(item: items.Axiom, raw: dict[str, Any]) -> str:
    """Return a theorem item's statement in the printer's notation.

    Parameters
    ----------
    item : holpy.server.items.Axiom
        Parsed theorem item.
    raw : dict
        Original JSON item, used as a fallback when parsing failed.

    Returns
    -------
    str
        The statement as printed, without the leading turnstile, or the raw
        proposition for an item that could not be parsed.
    """
    if item.error is None:
        with global_setting(unicode=True, highlight=False, line_length=None):
            rendered = printer.print_term(item.prop)
        if isinstance(rendered, list):
            return "\n".join(rendered)
        return rendered

    prop = raw.get("prop", "")
    if isinstance(prop, list):
        return "\n".join(str(part) for part in prop)
    return str(prop)


def _theorem_row(
    theory_name: str,
    index: int,
    item: items.Theorem,
    raw: dict[str, Any],
    check_level: int,
) -> Row:
    """Check one theorem item and convert the result to a row.

    Parameters
    ----------
    theory_name : str
        Name of the theory containing the theorem.
    index : int
        Index of the item in the theory's JSON content.
    item : holpy.server.items.Theorem
        Parsed theorem item.
    raw : dict
        Original JSON item.
    check_level : int
        Trust level passed to the kernel's proof checker.

    Returns
    -------
    Row
        ``fail`` if parsing or checking raises; ``noproof`` if there is
        no proof; ``gaps`` if the stored proof checks but contains at
        least one ``sorry`` line; ``ok`` otherwise.
    """
    statement = _printed_statement(item, raw)

    if item.error is not None:
        return Row(
            theory=theory_name,
            item=index,
            name=item.name,
            status="fail",
            error_type=item.error.__class__.__name__,
            statement=statement,
            steps=0,
            macros_eval="",
            time=0.0,
        )

    if item.proof is None:
        return Row(
            theory=theory_name,
            item=index,
            name=item.name,
            status="noproof",
            error_type="",
            statement=statement,
            steps=0,
            macros_eval="",
            time=0.0,
        )

    start = time.perf_counter()
    try:
        context.set_context(None, vars=item.vars)
        state = server.parse_proof(copy.deepcopy(item.proof))
        # ProofState.check_proof does not expose the kernel's check_level, so
        # call the kernel directly with a fresh report. This is the same check
        # that ProofState.check_proof performs.
        report = proof_report.ProofReport()
        state.rpt = report
        theory.check_proof(
            state.prf, rpt=report, no_gaps=False, check_level=check_level
        )
        elapsed = time.perf_counter() - start
        status = "gaps" if any(
            line.get("rule") == "sorry" for line in item.proof
        ) else "ok"
        return Row(
            theory=theory_name,
            item=index,
            name=item.name,
            status=status,
            error_type="",
            statement=statement,
            steps=report.steps,
            macros_eval=",".join(sorted(report.macros_eval)),
            time=round(elapsed, 2),
        )
    except Exception as exc:  # A failed certificate is data, not a crash.
        elapsed = time.perf_counter() - start
        logger.debug(
            "Theorem %s.%s failed", theory_name, item.name, exc_info=True
        )
        return Row(
            theory=theory_name,
            item=index,
            name=item.name,
            status="fail",
            error_type=exc.__class__.__name__,
            statement=statement,
            steps=0,
            macros_eval="",
            time=round(elapsed, 2),
        )


def process_theory(theory_name: str, check_level: int = 0) -> list[Row]:
    """Check every stored theorem proof in one theory.

    The theory is loaded only up to its dependencies, using the same pattern as
    ``prototypes/slim_check.py``.  Items are then parsed, checked and extended
    in JSON order.  Extending an item whose proof failed is intentional: later
    theorems may use its stated result, so one bad certificate does not turn
    the rest of the theory into cascading failures.

    Parameters
    ----------
    theory_name : str
        Name of the theory to check.
    check_level : int, optional
        Trust level passed to the kernel's proof checker.

    Returns
    -------
    list[Row]
        One row for each theorem item, in JSON item order.
    """
    start = time.perf_counter()
    basic.load_theory(theory_name, limit="start")
    data = basic.load_json_data(theory_name)
    rows: list[Row] = []

    for index, raw in enumerate(data["content"]):
        item = items.parse_item(raw)
        if item.ty == "thm":
            rows.append(_theorem_row(theory_name, index, item, raw, check_level))
        if item.error is None:
            theory.thy.unchecked_extend(item.get_extension())

    logger.info(
        "Checked theory %s: %d theorems in %.2f s",
        theory_name,
        len(rows),
        time.perf_counter() - start,
    )
    return rows


def _all_theories() -> list[str]:
    """Return every bundled theory name in import order.

    Returns
    -------
    list[str]
        Theory names such that dependencies precede their importers.
    """
    basic.load_metadata()
    names = sorted(path.stem for path in library_dir().glob("*.json"))
    return basic.get_import_order(names)


def run_theories(theory_names: Sequence[str], jobs: int, check_level: int = 0) -> list[Row]:
    """Check theories sequentially or in parallel and return ordered rows.

    Parameters
    ----------
    theory_names : sequence of str
        Theories to check.  The output follows this sequence, and rows within
        each theory follow JSON item order.
    jobs : int
        Number of worker processes.  ``1`` checks in the current process.
    check_level : int, optional
        Trust level passed to the kernel's proof checker.

    Returns
    -------
    list[Row]
        Rows for all requested theories.

    Raises
    ------
    ValueError
        If ``jobs`` is less than one.
    """
    if jobs < 1:
        raise ValueError("jobs must be at least 1")

    if jobs == 1 or len(theory_names) <= 1:
        results = [process_theory(name, check_level) for name in theory_names]
    else:
        with multiprocessing.Pool(min(jobs, len(theory_names))) as pool:
            results = pool.starmap(
                process_theory, [(name, check_level) for name in theory_names]
            )

    # The pool preserves input order, but sorting by the requested theory order
    # also makes the invariant explicit and keeps explicit theory arguments in
    # the order the caller gave them.
    theory_order = {name: index for index, name in enumerate(theory_names)}
    rows = [row for group in results for row in group]
    rows.sort(key=lambda row: (theory_order[row.theory], row.item))
    return rows


def write_tsv(rows: Sequence[Row], out_path: Path) -> None:
    """Write rows as a deterministic, escaped TSV file.

    Parameters
    ----------
    rows : sequence of Row
        Rows to write.
    out_path : pathlib.Path
        Destination file.  Parent directories are created as needed.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        f.write("\t".join(COLUMNS) + "\n")
        for row in rows:
            values = (
                row.theory,
                row.name,
                row.status,
                row.error_type,
                row.statement,
                str(row.steps),
                row.macros_eval,
                f"{row.time:.2f}",
            )
            f.write("\t".join(_escape_field(value) for value in values) + "\n")


def read_tsv(path: Path) -> tuple[list[str], dict[tuple[str, str], dict[str, str]]]:
    """Read a check-library TSV file.

    Parameters
    ----------
    path : pathlib.Path
        TSV file to read.

    Returns
    -------
    tuple of (list of str, dict)
        The header and a mapping from ``(theory, name)`` to the row fields.

    Raises
    ------
    ValueError
        If the file is empty or lacks the required columns.
    """
    with path.open(encoding="utf-8", newline="") as f:
        lines = f.read().splitlines()
    if not lines:
        raise ValueError(f"{path}: empty TSV file")

    header = lines[0].split("\t")
    missing = [column for column in COLUMNS if column not in header]
    if missing:
        raise ValueError(f"{path}: missing columns: {', '.join(missing)}")

    rows: dict[tuple[str, str], dict[str, str]] = {}
    for line_number, line in enumerate(lines[1:], start=2):
        parts = line.split("\t")
        if len(parts) != len(header):
            raise ValueError(
                f"{path}:{line_number}: expected {len(header)} fields, "
                f"got {len(parts)}"
            )
        fields = dict(zip(header, parts))
        key = (fields["theory"], fields["name"])
        rows[key] = fields
    return header, rows


def _total_time(rows: dict[tuple[str, str], dict[str, str]]) -> float:
    """Return the sum of the ``time`` fields in a parsed TSV.

    Parameters
    ----------
    rows : dict
        Parsed rows from :func:`read_tsv`.

    Returns
    -------
    float
        Total checking time in seconds.
    """
    total = 0.0
    for fields in rows.values():
        try:
            total += float(fields["time"])
        except (KeyError, ValueError):
            continue
    return total


def compare_files(old_path: Path, new_path: Path) -> int:
    """Compare two check-library TSV files.

    The comparison reports differences in ``status``, ``statement`` and
    ``steps`` and prints the total time in both files.  A theorem that was
    ``ok`` before and is not ``ok`` now (or is missing from the new file) makes
    the comparison fail.

    Parameters
    ----------
    old_path : pathlib.Path
        Baseline TSV file.
    new_path : pathlib.Path
        New TSV file.

    Returns
    -------
    int
        ``1`` if a theorem went from ``ok`` to another state, otherwise ``0``.
    """
    _, old_rows = read_tsv(old_path)
    _, new_rows = read_tsv(new_path)

    differences: list[tuple[tuple[str, str], str, str, str]] = []
    degraded: list[tuple[str, str]] = []

    for key in sorted(old_rows.keys() | new_rows.keys()):
        theorem = f"{key[0]}.{key[1]}"
        if key not in old_rows:
            logger.info("%s: only in the new file", theorem)
            continue
        if key not in new_rows:
            logger.info("%s: missing from the new file", theorem)
            if old_rows[key]["status"] == "ok":
                degraded.append(key)
            continue

        old_fields = old_rows[key]
        new_fields = new_rows[key]
        for column in COMPARE_COLUMNS:
            if old_fields[column] != new_fields[column]:
                differences.append(
                    (key, column, old_fields[column], new_fields[column])
                )

        if old_fields["status"] == "ok" and new_fields["status"] != "ok":
            degraded.append(key)

    old_total = _total_time(old_rows)
    new_total = _total_time(new_rows)
    logger.info("Total time: before %.2f s, after %.2f s", old_total, new_total)

    if differences:
        for key, column, old_value, new_value in differences:
            logger.info(
                "%s.%s: %s changed from %r to %r",
                key[0],
                key[1],
                column,
                old_value,
                new_value,
            )
    else:
        logger.info("No differences in status, statement or steps.")

    if degraded:
        logger.warning(
            "Theorems that went from ok to another status: %s",
            ", ".join(f"{theory_name}.{name}" for theory_name, name in degraded),
        )
        return 1
    return 0


def _report_quarantine(rows: Sequence[Row]) -> None:
    """Log which gap rows are listed in the quarantine index.

    Parameters
    ----------
    rows : sequence of Row
        All rows from the current check.
    """
    index_path = _REPO_ROOT / "docs" / "quarantine" / "INDEX.md"
    if not index_path.exists():
        return

    index_lines = index_path.read_text(encoding="utf-8").lower().splitlines()
    listed: list[str] = []
    not_listed: list[str] = []
    for row in rows:
        if row.status != "gaps":
            continue
        name = f"{row.theory}.{row.name}"
        slash_name = f"{row.theory}/{row.name}"
        found = any(
            name.lower() in line
            or slash_name.lower() in line
            or (row.theory.lower() in line and row.name.lower() in line)
            for line in index_lines
        )
        (listed if found else not_listed).append(name)

    if listed:
        logger.info("Quarantined (listed): %s", ", ".join(listed))
    if not_listed:
        logger.info("Quarantined (not listed): %s", ", ".join(not_listed))


def _positive_int(value: str) -> int:
    """Parse a strictly positive integer for argparse.

    Parameters
    ----------
    value : str
        Command-line value.

    Returns
    -------
    int
        The parsed integer.

    Raises
    ------
    argparse.ArgumentTypeError
        If the value is not a positive integer.
    """
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer: {value!r}") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns
    -------
    argparse.ArgumentParser
        Parser for the check-library command.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Check stored proofs in the holpy library. "
            "Status is gaps when a proof checks but contains a sorry line."
        )
    )
    parser.add_argument(
        "theory",
        nargs="*",
        help="theory names to check (default: every bundled theory)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/library_check.tsv"),
        help="output TSV file (default: %(default)s)",
    )
    parser.add_argument(
        "--jobs",
        type=_positive_int,
        default=1,
        help="number of worker processes (default: %(default)s)",
    )
    parser.add_argument(
        "--check-level",
        type=int,
        default=0,
        help="trust level passed to the kernel proof checker (default: %(default)s)",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        type=Path,
        metavar=("OLD", "NEW"),
        help="compare two TSV files instead of checking theorems",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the library checker.

    Parameters
    ----------
    argv : sequence of str, optional
        Command-line arguments, excluding the program name.

    Returns
    -------
    int
        Process exit status.  Checking exits 0 even when proofs fail; a
        comparison exits 1 only when a theorem went from ``ok`` to another
        state.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )

    if args.compare:
        if args.theory:
            logger.warning("Ignoring theory arguments in --compare mode")
        return compare_files(args.compare[0], args.compare[1])

    # The cache is keyed only by the master user, while HOLPY_LIBRARY_DIR can
    # change between calls in an embedding process. Start from the current
    # library location rather than a previous caller's parsed theories.
    basic.theory_cache.clear()
    basic.item_index.clear()

    theory_names = list(args.theory) if args.theory else _all_theories()
    rows = run_theories(theory_names, args.jobs, args.check_level)
    write_tsv(rows, args.out)
    _report_quarantine(rows)
    logger.info("Wrote %d rows to %s", len(rows), args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
