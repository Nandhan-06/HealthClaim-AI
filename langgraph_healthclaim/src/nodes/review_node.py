"""
review_node.py — Node 3 of 4
============================
Checks the current decision (draft_decision on the first pass, or
revised_decision after a loop-back) against the actually retrieved
policy/provider/history/diagnosis data: does the payable amount respect
the room-rent cap and remaining sum insured? Was a duplicate or fraud
signal missed? Is the procedure justified by the diagnosis? Writes
review_verdict + review_flags, which route_after_review inspects.
"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.data_loader import get_default_store  # noqa: E402
from shared.models import ClaimDecision  # noqa: E402
from shared.rule_engine import review_decision as _review  # noqa: E402

from ..state import ClaimState


def review_decision(state: ClaimState) -> ClaimState:
    store = get_default_store()
    current_dict = state.get("revised_decision") or state["draft_decision"]
    current = ClaimDecision(**current_dict)

    verdict, flags, ground_truth = _review(state["claim_request"], current, store)
    current.verdict = verdict

    return {
        **state,
        "review_verdict": verdict,
        "review_flags": flags,
        "ground_truth_decision": ground_truth.to_dict(),
        "final_decision": current.to_dict() if verdict == "PASS" else state.get("final_decision", {}),
    }
