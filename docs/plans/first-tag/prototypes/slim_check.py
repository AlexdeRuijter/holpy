"""Prototype: does a theory's stored proof still check with `th` on fewer lines?

Throwaway measurement script written while planning the first tag
(2026-10-28). It is not part of the package and has no tests.

Usage, from the repository root::

    PYTHONPATH=. python docs/plans/first-tag/prototypes/slim_check.py THEORY [KEEP]

``KEEP`` is a comma-separated list of rule names whose lines keep ``th``
(default ``sorry``). For every theorem with a stored ``proof`` the script
checks the proof twice, as stored ("full") and with ``th`` blanked on every
other line except the last ("slim"), and prints counts, mismatches and the
total check time of each mode. Theorems whose slim check takes over 3 s are
printed as ``SLOW``.

Results on main at cf4f524:

    logic  full 45 ok / slim 45 ok, 0 mismatches, 0.8 s / 0.5 s
    set    full 85 ok / slim 84 ok, 0 mismatches, 6.6 s / 208 s (nat_finite: 198 s)
    nat    full 214 ok / slim 214 ok, 0 mismatches, 13.8 s / 9.7 s
"""
import copy
import sys
import time

from holpy.kernel import theory
from holpy.logic import basic, context
from holpy.server import items, server

name = sys.argv[1]
KEEP = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else {'sorry'}
data = basic.load_json_data(name)
basic.load_theory(name, limit='start')
stat = {'full_ok': 0, 'slim_ok': 0, 'full_fail': 0, 'slim_fail': 0, 'mismatch': 0}
t_full = t_slim = 0.0
for raw in data['content']:
    it = items.parse_item(raw)
    if it.error is None:
        exts = it.get_extension()
    if it.ty == 'thm' and it.error is None and it.proof:
        full_th = None
        for mode in ('full', 'slim'):
            prf = copy.deepcopy(it.proof)
            if mode == 'slim':
                for i, line in enumerate(prf):
                    if i != len(prf) - 1 and line['rule'] not in KEEP:
                        line['th'] = ''
            t0 = time.perf_counter()
            try:
                context.set_context(None, vars=it.vars)
                st = server.parse_proof(prf)
                th = st.check_proof(no_gaps=False)
                stat[mode + '_ok'] += 1
                if mode == 'full':
                    full_th = str(th)
                elif str(th) != full_th:
                    stat['mismatch'] += 1
            except Exception:
                stat[mode + '_fail'] += 1
            dt = time.perf_counter() - t0
            if mode == 'full':
                t_full += dt
            else:
                t_slim += dt
                if dt > 3:
                    print('SLOW', it.name, round(dt, 1))
    if it.error is None:
        theory.thy.unchecked_extend(exts)
print(name, stat, 'full %.1fs slim %.1fs' % (t_full, t_slim))
