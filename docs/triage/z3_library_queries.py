"""Record every Z3 query the library check issues, and re-run it in proof mode.

    PYTHONPATH=. python docs/triage/z3_library_queries.py THEORY... --out DIR [--proof-timeout S]

For each theory (checked in this process, like scripts/check_library.py does) the script
wraps ``holpy.prover.z3wrapper.solve`` and appends one JSON object per call to
``DIR/queries.jsonl``:

* theory, theorem (name of the theorem being parsed/checked), index (call number)
* sha: hash of the SMT-LIB text; smt2: the query as ``Solver.to_smt2()`` (default context)
* result, seconds: the answer of ``z3wrapper.solve`` (proof mode off), qsat: whether the
  statistics show the ``qsat`` procedure ran
* proof_result, proof_seconds: the same query in a private ``z3.Context(proof=True)`` as
  ``solve_and_proof`` builds it (once per distinct sha; ``unsat`` / ``unknown`` / ``sat``)

``DIR/summary.txt`` counts the queries; the interesting rows are those that are ``unsat``
without proofs but not ``unsat`` with proof mode (these cannot be proof-reconstructed).
Optionally ``--smt2-dir`` also writes one ``.smt2`` file per distinct query.
"""
import argparse, hashlib, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("theories", nargs="+")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--proof-timeout", type=float, default=10)
    ap.add_argument("--z3-timeout", type=float, default=60)
    ap.add_argument("--smt2-dir", type=Path)
    ap.add_argument("--seeds", type=int, default=0,
                    help="also solve every distinct query (parsed from its SMT-LIB text) with "
                    "smt.random_seed 0..N-1 and record U (unsat) / k (anything else) per seed")
    ap.add_argument("--seed-timeout", type=float, default=3)
    ap.add_argument("--report-dir", type=Path,
                    help="write fragile.tsv, summary.txt and the SMT-LIB files of the fragile "
                    "queries here (small enough to commit)")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if a.smt2_dir:
        a.smt2_dir.mkdir(parents=True, exist_ok=True)

    import z3
    from holpy.prover import z3wrapper
    from holpy.server import items
    from scripts import check_library

    z3.set_param("timeout", int(a.z3_timeout * 1000))
    cur = {"theory": None, "theorem": None}
    seen = {}
    sweeps = {}
    out = (a.out / "queries.jsonl").open("w", encoding="utf-8")
    real_solve = z3wrapper.solve
    real_parse = items.parse_item
    count = [0]

    def parse_item(raw, *args, **kw):
        if isinstance(raw, dict):
            cur["theorem"] = raw.get("name")
        return real_parse(raw, *args, **kw)

    def solve(t, debug=False):
        s = z3wrapper.solve_core(z3.Solver(), t, debug)
        smt2 = s.to_smt2()
        t0 = time.perf_counter()
        r = str(s.check())
        dt = time.perf_counter() - t0
        st = s.statistics()
        sha = hashlib.sha1(smt2.encode()).hexdigest()[:12]
        rec = dict(theory=cur["theory"], theorem=cur["theorem"], index=count[0], sha=sha,
                   result=r, seconds=round(dt, 3), qsat="qsat num rounds" in st.keys(), smt2=smt2)
        count[0] += 1
        if sha not in seen:
            pr, pdt = "error", 0.0
            try:
                ps = z3wrapper.solve_core(z3.Solver(ctx=z3.Context(proof=True)), t, debug)
                ps.set("timeout", int(a.proof_timeout * 1000))
                t0 = time.perf_counter()
                pr = str(ps.check())
                pdt = time.perf_counter() - t0
            except Exception as e:  # noqa: BLE001
                pr = "error: %s" % str(e)[:80]
            seen[sha] = (pr, round(pdt, 3))
            if a.smt2_dir:
                (a.smt2_dir / ("%s.smt2" % sha)).write_text(smt2, encoding="utf-8")
        if sha not in sweeps:
            sw = ""
            for sd in range(a.seeds):
                ss = z3.Solver()
                ss.set("timeout", int(a.seed_timeout * 1000))
                ss.set("random_seed", sd)
                ss.from_string(smt2)
                sw += "U" if str(ss.check()) == "unsat" else "k"
            sweeps[sha] = sw
        rec["seeds"] = sweeps[sha]
        rec["proof_result"], rec["proof_seconds"] = seen[sha]
        out.write(json.dumps(rec) + "\n")
        out.flush()
        return r == "unsat"

    z3wrapper.solve = solve
    items.parse_item = parse_item
    check_library.items.parse_item = parse_item

    for th in a.theories:
        cur["theory"] = th
        check_library.process_theory(th, 0)
    out.close()

    rows = [json.loads(l) for l in (a.out / "queries.jsonl").open(encoding="utf-8")]
    distinct = {r["sha"]: r for r in rows}
    lines = ["theories: %s" % " ".join(a.theories), "z3 %s" % z3.get_version_string(),
             "queries: %d calls, %d distinct" % (len(rows), len(distinct))]
    for label, sel in (("calls", rows), ("distinct", list(distinct.values()))):
        n = len(sel)
        unsat = [r for r in sel if r["result"] == "unsat"]
        qs = [r for r in unsat if r["qsat"]]
        weak = [r for r in unsat if r["proof_result"] != "unsat"]
        weakq = [r for r in weak if r["qsat"]]
        lines.append("%s: %d; unsat %d; of those qsat ran %d; not unsat in proof mode %d (qsat ran %d)"
                     % (label, n, len(unsat), len(qs), len(weak), len(weakq)))
    lines.append("not unsat in proof mode (distinct): " + ", ".join(
        sorted({"%s.%s" % (r["theory"], r["theorem"]) for r in distinct.values()
                if r["result"] == "unsat" and r["proof_result"] != "unsat"})))
    fragile = [r for r in distinct.values()
               if r["result"] != "unsat" or r["proof_result"] != "unsat" or "k" in r["seeds"]]
    lines.append("distinct queries answered unsat in the run: %d" % sum(r["result"] == "unsat" for r in distinct.values()))
    lines.append("fragile distinct queries (not unsat in the run, or in proof mode, or for some seed): %d"
                 % len(fragile))
    lines.append("  of which unknown in the run itself: %d" % sum(r["result"] != "unsat" for r in fragile))
    lines.append("  of which seed-dependent (k for some but not all seeds): %d"
                 % sum(0 < r["seeds"].count("k") < len(r["seeds"]) for r in fragile))
    (a.out / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if a.report_dir:
        a.report_dir.mkdir(parents=True, exist_ok=True)
        (a.report_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        with (a.report_dir / "fragile.tsv").open("w", encoding="utf-8") as f:
            f.write("sha\ttheory\ttheorem\tresult\tseconds\tqsat\tproof_result\tseeds\n")
            for r in sorted(fragile, key=lambda r: (r["theory"], r["theorem"] or "", r["sha"])):
                f.write("\t".join(str(x) for x in (r["sha"], r["theory"], r["theorem"], r["result"],
                        r["seconds"], r["qsat"], r["proof_result"], r["seeds"])) + "\n")
                d = a.report_dir / "smt2"
                d.mkdir(exist_ok=True)
                (d / ("%s.smt2" % r["sha"])).write_text(r["smt2"], encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
