#!/usr/bin/env python
"""Library proof check tool for holpy."""

from __future__ import annotations

import argparse
import copy
import json
import logging
import multiprocessing
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, ".")

from holpy.logic import basic
from holpy.logic import context
from holpy.server import items, server
from holpy.syntax import printer
from holpy.syntax.settings import settings, global_setting
from holpy.kernel import theory

logger = logging.getLogger("check_library")


def load_order():
    basic.load_metadata()
    return basic.get_import_order(list(basic.theory_cache["master"].keys()))


def check_theory_args(theory_name: str) -> list[dict]:
    basic.load_theory(theory_name)
    data = basic.load_json_data(theory_name)
    results: list[dict] = []
    for raw in data["content"]:
        it = items.parse_item(raw)
        if it.ty == "thm" and it.error is None and it.proof is not None:
            status = "noproof" if it.proof is None else None
            # handled below
            pass
        # Process below
        results.append((theory_name, it))
    # Actually we'll process in loop
    return []


def process_theory(theory_name: str) -> list[dict]:
    basic.load_theory(theory_name)
    data = basic.load_json_data(theory_name)
    # Monkey-patch has_theorem to allow parsing current theory items
    original_has_theorem = theory.thy.has_theorem
    theory.thy.has_theorem = lambda name: False
    rows: list[dict] = []
    for raw in data["content"]:
        it = items.parse_item(raw)
        theory.thy.has_theorem = original_has_theorem  # restore temporarily if needed
        # Restore monkey-patch for next parse? Actually parse_item uses it.
        # We need to keep monkey-patch until all items parsed.
        # But after parse_item, we can restore.
        # Let's just keep monkey-patch active during the loop.
        theory.thy.has_theorem = lambda name: False
        if it.ty != "thm":
            continue
        if it.error is not None:
            continue
        name = it.name
        raw_prop_str = raw.get('prop', '')
        if it.proof is None:
            rows.append({
                "theory": theory_name,
                "name": name,
                "status": "noproof",
                "error_type": "",
                "statement": "",
                "steps": 0,
                "macros_eval": "",
                "time": 0.0,
            })
            continue
        t0 = time.perf_counter()
        try:
            context.set_context(None, vars=it.vars)
            state = server.parse_proof(copy.deepcopy(it.proof))
            state.check_proof(no_gaps=False)
            rpt = state.rpt
            time_taken = time.perf_counter() - t0
            gaps = len(rpt.gaps) if rpt else 0
            status = "gaps" if gaps > 0 else "ok"
            error_type = ""
            stmt = raw_prop_str
            steps_count = rpt.steps if rpt else 0
            macros_eval = ",".join(sorted(rpt.macros_eval)) if rpt else ""
            rows.append({
                "theory": theory_name,
                "name": name,
                "status": status,
                "error_type": error_type,
                "statement": stmt,
                "steps": steps_count,
                "macros_eval": macros_eval,
                "time": round(time_taken, 2),
            })
        except Exception as exc:
            time_taken = time.perf_counter() - t0
            error_type = exc.__class__.__name__
            stmt = raw_prop_str
            rows.append({
                "theory": theory_name,
                "name": name,
                "status": "fail",
                "error_type": error_type,
                "statement": stmt,
                "steps": 0,
                "macros_eval": "",
                "time": round(time_taken, 2),
            })
    return rows


def run_theories(theory_names: list[str], jobs: int) -> list[dict]:
    if jobs <= 1 or len(theory_names) <= 1:
        results = []
        for name in theory_names:
            logger.info("Checking theory %s", name)
            results.extend(process_theory(name))
        return results
    with multiprocessing.Pool(jobs) as pool:
        results = pool.map(process_theory, theory_names)
    rows = []
    for r in results:
        rows.extend(r)
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("theory", nargs="*", default=[])
    parser.add_argument("--out", default="docs/library_check.tsv")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--check-level", type=int, default=0)
    parser.add_argument("--compare", nargs=2, metavar=("OLD", "NEW"), default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if args.compare:
        old_path, new_path = args.compare
        compare_files(old_path, new_path)
        return

    if args.theory:
        theory_names = args.theory
    else:
        theory_names = load_order()

    rows = run_theories(theory_names, args.jobs)
    # Sort by theory then item order (preserve data order per theory since we iterated content)
    # The content order is preserved within each theory; sorting just by theory and then index not needed because rows are appended in content order per theory.
    # But if we run in parallel, the order of theories may vary; we need deterministic order by theory name.
    rows.sort(key=lambda r: (r["theory"], r["name"]))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="") as f:
        f.write("theory\tname\tstatus\terror_type\tstatement\tsteps\tmacros_eval\ttime\n")
        for r in rows:
            f.write(
                f"{r['theory']}\t{r['name']}\t{r['status']}\t{r['error_type']}\t"
                f"{r['statement']}\t{r['steps']}\t{r['macros_eval']}\t{r['time']}\n"
            )

    # Quarantine info
    index_path = Path("docs/quarantine/INDEX.md")
    if index_path.exists():
        index_content = index_path.read_text().lower()
        gaps_rows = [r for r in rows if r["status"] == "gaps"]
        listed = []
        not_listed = []
        for r in gaps_rows:
            key = f"{r['theory']}/{r['name']}".lower()
            if key in index_content or r["name"].lower() in index_content:
                listed.append(r)
            else:
                not_listed.append(r)
        if listed:
            print("Quarantined (listed):", ", ".join(f"{r['theory']}.{r['name']}" for r in listed))
        if not_listed:
            print("Quarantined (not listed):", ", ".join(f"{r['theory']}.{r['name']}" for r in not_listed))


def compare_files(old_path: str, new_path: str):
    def load_rows(p):
        with open(p, newline="") as f:
            lines = f.read().splitlines()
        header = lines[0].split("\t")
        rows = {}
        for line in lines[1:]:
            parts = line.split("\t")
            key = (parts[0], parts[1])
            rows[key] = parts
        return rows

    old_rows = load_rows(old_path)
    new_rows = load_rows(new_path)
    diffs = []
    for key, new_parts in new_rows.items():
        if key not in old_rows:
            continue
        old_parts = old_rows[key]
        for i in range(2, len(old_parts)):
            field = header[i] if 'header' in locals() else None
            if i < len(new_parts) and old_parts[i] != new_parts[i]:
                if field == "status" or field == "statement" or field == "steps":
                    diffs.append((key, field, old_parts[i], new_parts[i]))
    # Actually let's just compare status, statement, steps properly
    header = None
    with open(old_path, newline="") as f:
        header = f.readline().strip().split("\t")
    for key in sorted(old_rows.keys()):
        if key not in new_rows:
            continue
        old_line = old_rows[key]
        new_line = new_rows[key]
        for i, col in enumerate(header):
            if col in ("status", "statement", "steps"):
                idx = header.index(col)
                if idx < len(old_line) and idx < len(new_line):
                    if old_line[idx] != new_line[idx]:
                        diffs.append((key, col, old_line[idx], new_line[idx]))

    # Also check for ok -> fail
    degraded = []
    for key in sorted(old_rows.keys()):
        if key not in new_rows:
            continue
        old_status_idx = header.index("status")
        new_status_idx = header.index("status")
        old_status = old_rows[key][old_status_idx]
        new_status = new_rows[key][new_status_idx]
        if old_status == "ok" and new_status != "ok":
            degraded.append(key)

    old_time = sum(float(r[header.index("time")]) for r in old_rows.values()) if header else 0
    new_time = sum(float(r[header.index("time")]) for r in new_rows.values()) if header else 0

    print("Old time: %.2f s, New time: %.2f s" % (old_time, new_time))
    if diffs:
        for d in diffs:
            print("Difference %s %s: %s -> %s" % (d[0][0] + "." + d[0][1], d[1], d[2], d[3]))
    else:
        print("No differences in status/statement/steps.")
    if degraded:
        print("Degraded from ok:", ", ".join(f"{k[0]}.{k[1]}" for k in degraded))
    sys.exit(1 if degraded else 0)


if __name__ == "__main__":
    main()
