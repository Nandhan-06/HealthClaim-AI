"""
state.py
========
The explicit ClaimState that flows through the LangGraph StateGraph.
Every node reads from and writes back into this single object — this is
the thing that makes LangGraph a state machine rather than a pipeline.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class ClaimState(TypedDict, total=False):
    # --- input -------------------------------------------------------
    raw_claim: Dict[str, Any]

    # --- written by intake_claim (Node 1) -----------------------------
    claim_request: Dict[str, Any]        # ClaimRequest.to_dict()
    intake_errors: List[str]

    # --- written by triage_claim (Node 2) -----------------------------
    draft_decision: Dict[str, Any]       # ClaimDecision.to_dict()

    # --- written by review_decision (Node 3) --------------------------
    review_verdict: str                  # "PASS" | "REVISE"
    review_flags: List[str]
    ground_truth_decision: Dict[str, Any]

    # --- written by revise_decision (Node 4) --------------------------
    revised_decision: Dict[str, Any]

    # --- loop bookkeeping (used by route_after_review) ----------------
    iteration: int
    max_iterations: int

    # --- final ----------------------------------------------------------
    final_decision: Dict[str, Any]
