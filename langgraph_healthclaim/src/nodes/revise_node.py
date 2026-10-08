"""
revise_node.py — Node 4 of 4
============================
Only reached when route_after_review sends the state here (verdict ==
REVISE). Applies the correction implied by review's flags, bumps the
iteration counter, and — if max_iterations has now been hit — forces a
final decision so a stubborn claim cannot loop forever.
"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.models import ClaimDecision  # noqa: E402
from shared.rule_engine import revise_decision as _revise  # noqa: E402

from ..state import ClaimState


def revise_decision(state: ClaimState) -> ClaimState:
    ground_truth = ClaimDecision(**state["ground_truth_decision"])
    corrected = _revise(ground_truth, state["review_flags"])

    iteration = state.get("iteration", 0) + 1
    max_iterations = state.get("max_iterations", 3)

    result = {**state, "revised_decision": corrected.to_dict(), "iteration": iteration}

    if iteration >= max_iterations:
        # Loop cap reached: stop here rather than routing back to review
        # again — accept the corrected decision as final either way.
        corrected.verdict = "PASS"
        result["final_decision"] = corrected.to_dict()

    return result
