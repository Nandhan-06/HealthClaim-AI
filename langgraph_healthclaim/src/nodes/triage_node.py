"""
triage_node.py — Node 2 of 4
============================
Runs the (intentionally incomplete) first-draft rule engine using the
policy / provider / history / diagnosis tools, and writes draft_decision
into ClaimState. On a loop-back this node is skipped (LangGraph routes
straight from revise_decision back to review_decision) — see graph.py.
"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.data_loader import get_default_store  # noqa: E402
from shared.rule_engine import naive_triage  # noqa: E402

from ..state import ClaimState


def triage_claim(state: ClaimState) -> ClaimState:
    store = get_default_store()
    draft = naive_triage(state["claim_request"], store)
    return {**state, "draft_decision": draft.to_dict()}
