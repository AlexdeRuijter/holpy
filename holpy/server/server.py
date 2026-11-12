# Author: Bohua Zhan

import copy
import itertools
from typing import List, Union

from holpy.kernel import term
from holpy.kernel.term import Term, Var
from holpy.kernel.thm import Thm
from holpy.kernel.proof import ProofItem, Proof, ItemID, ProofStateException
from holpy.kernel import report
from holpy.kernel import theory
from holpy.kernel.proofterm import ProofTerm
from holpy.logic import logic, matcher
from holpy.logic import context
from holpy.logic import tactic
from holpy.logic.context import Context
from holpy.syntax import parser, printer
from holpy.syntax.settings import settings, global_setting
from holpy.server.method import ProofState
from holpy.util import typecheck


def parse_init_state(prop: Union[str, List[str], Term]) -> ProofState:
    """Given data for a theorem statement, construct the initial partial proof.
    
    data['vars']: list of variables.
    data['prop']: proposition to be proved. In the form A1 --> ... --> An --> C.

    Construct initial partial proof for the given assumptions and
    conclusion.

    assums - assumptions A1, ... An.
    concl - conclusion C.
    
    Constructs:

    0: assume A1
    ...
    n-1: assume An
    n: C by sorry
    n+1: A1 --> ... --> An --> C by intros from 0, 1, ..., n.

    """
    typecheck.checkinstance('parse_init_state', prop, (str, list, Term))
    if isinstance(prop, (str, list)):
       prop = parser.parse_term(prop)
    assums, concl = prop.strip_implies()

    state = ProofState()
    for nm, T in context.ctxt.vars.items():
        state.vars.append(Var(nm, T))
    state.prf = Proof(*assums)
    n = len(assums)
    state.prf.add_item(n, "sorry", th=Thm(concl, tuple(assums)))
    state.prf.add_item(n + 1, "intros", prevs=range(n+1))
    state.check_proof(compute_only=True)
    return state

def parse_proof(proof, check: bool = True) -> ProofState:
    """Obtain proof from json format.

    Parameters
    ----------
    proof : list of dict
        Stored proof lines in JSON form.
    check : bool, optional
        Whether to check the parsed proof before returning the state. Callers
        that check it themselves, with their own report or trust level, pass
        ``False``.

    Returns
    -------
    ProofState
        State containing the parsed proof and the current context variables.
    """
    state = ProofState()
    for nm, T in context.ctxt.vars.items():
        state.vars.append(Var(nm, T))
    state.prf = Proof()
    # A variable declared in a subproof is scoped to that subproof.  The
    # parent path of a line id selects the subproof: for example, 2.11.0 is
    # inside subproof 2.11.  Save the variable context on entry and restore
    # it when moving to a sibling or enclosing proof.
    var_scopes = []
    for line in proof:
        path = ItemID(line['id']).id[:-1]
        scope_path = path
        while var_scopes and var_scopes[-1][0] != scope_path[:len(var_scopes[-1][0])]:
            _, saved_vars = var_scopes.pop()
            context.ctxt.vars = saved_vars
        while len(var_scopes) < len(scope_path):
            var_scopes.append((scope_path[:len(var_scopes) + 1],
                               dict(context.ctxt.vars)))
        if line['rule'] == "variable":
            nm, str_T = line['args'].split(',', 1)
            context.ctxt.vars[nm] = parser.parse_type(str_T.strip())
        if line['rule'] == "intros" and var_scopes and line.get('th', '') != "":
            # An intros line closes its subproof: its arguments may mention
            # variables declared in the body, but the resulting theorem is
            # stated in the enclosing context.
            item = parser.parse_proof_rule(dict(line, th=''))
            body_vars = context.ctxt.vars
            context.ctxt.vars = var_scopes[-1][1]
            try:
                item.th = parser.parse_thm(line['th'])
            finally:
                context.ctxt.vars = body_vars
        else:
            item = parser.parse_proof_rule(line)
        state.prf.insert_item(item)

    while var_scopes:
        _, saved_vars = var_scopes.pop()
        context.ctxt.vars = saved_vars
    if check:
        state.check_proof()

    return state
