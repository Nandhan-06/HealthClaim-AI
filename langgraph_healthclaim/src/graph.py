"""
graph.py
========
Assembles the 4-node, 1-conditional-edge LangGraph StateGraph:

    intake_claim -> triage_claim -> review_decision --PASS--> END
                                          ^                |
                                          |               REVISE
                                          |                v
                                          +---- revise_decision

route_after_review() is the single conditional edge; every other edge
is a fixed, unconditional transition.
"""

from langgraph.graph import StateGraph, END

from .state import ClaimState
from .nodes import intake_claim, triage_claim, review_decision, revise_decision
from .edges import route_after_review


def build_graph():
    graph = StateGraph(ClaimState)

    graph.add_node("intake_claim", intake_claim)
    graph.add_node("triage_claim", triage_claim)
    graph.add_node("review_decision", review_decision)
    graph.add_node("revise_decision", revise_decision)

    graph.set_entry_point("intake_claim")
    graph.add_edge("intake_claim", "triage_claim")
    graph.add_edge("triage_claim", "review_decision")

    graph.add_conditional_edges(
        "review_decision",
        route_after_review,
        {END: END, "revise_decision": "revise_decision"},
    )
    graph.add_edge("revise_decision", "review_decision")

    return graph.compile()
