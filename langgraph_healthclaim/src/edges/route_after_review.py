"""
route_after_review.py — the 1 conditional edge
===============================================
Inspects review_verdict at runtime to decide whether to loop back to
revise_decision or stop at END. This is the whole teaching point of the
LangGraph version: a genuine runtime branch that CrewAI's sequential
Process cannot express.
"""

from langgraph.graph import END

from ..state import ClaimState


def route_after_review(state: ClaimState) -> str:
    if state["review_verdict"] == "PASS":
        return END
    # Loop cap: revise_decision itself also force-stops at max_iterations,
    # but guarding here too keeps the routing logic self-explanatory.
    if state.get("iteration", 0) >= state.get("max_iterations", 3):
        return END
    return "revise_decision"
