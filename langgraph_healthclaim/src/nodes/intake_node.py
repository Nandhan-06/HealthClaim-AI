"""
intake_node.py — Node 1 of 4
============================
Reads the raw claim dict and turns it into a clean, structured
ClaimRequest, writing it into ClaimState. Also seeds the loop
bookkeeping (iteration / max_iterations) that route_after_review reads.
"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.models import ClaimRequest  # noqa: E402
from shared.rule_engine import MAX_ITERATIONS  # noqa: E402

from ..state import ClaimState


def intake_claim(state: ClaimState) -> ClaimState:
    errors = []
    claim_request_dict = {}
    try:
        claim_request = ClaimRequest.from_raw(state["raw_claim"])
        claim_request_dict = claim_request.to_dict()
    except ValueError as exc:
        errors.append(str(exc))

    return {
        **state,
        "claim_request": claim_request_dict,
        "intake_errors": errors,
        "iteration": 0,
        "max_iterations": state.get("max_iterations", MAX_ITERATIONS),
    }
