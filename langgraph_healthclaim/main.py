"""
main.py — LangGraph HealthClaim AI
===================================
Runs every case in data/health_sample_test_inputs.json through the
4-node LangGraph StateGraph and prints a formatted decision report for
each, plus a summary of how many revision loops each case needed.

Usage:
    cd langgraph_healthclaim
    pip install -r requirements.txt   # langgraph, langchain-core, (langchain-openai + python-dotenv optional)
    cp .env.example .env              # optional: add a real OPENAI_API_KEY
    python main.py
"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from shared.data_loader import get_default_store
from shared.models import ClaimDecision

from src.graph import build_graph


def run_all():
    store = get_default_store()
    test_cases = store.load_sample_test_inputs()
    graph = build_graph()

    summary = []
    for case in test_cases:
        state = {"raw_claim": case["claim"]}
        result = graph.invoke(state)

        final = result.get("final_decision") or result.get("revised_decision") or result["draft_decision"]
        decision = ClaimDecision(**final)
        iterations = result.get("iteration", 0)

        print(f"--- {case['id']}: {case['description']} ---")
        print(decision.format_report(case["claim"]["claim_id"]))
        print(f"Revision loops used: {iterations}")
        print()

        summary.append((case["id"], decision.status, decision.verdict, iterations))

    print("=== Summary ===")
    for case_id, status, verdict, iterations in summary:
        print(f"{case_id}: status={status:<22} verdict={verdict:<6} revise_loops={iterations}")

    revised_cases = [c for c in summary if c[3] > 0]
    print(f"\n{len(revised_cases)} of {len(summary)} cases required at least one REVISE loop: "
          f"{[c[0] for c in revised_cases]}")


if __name__ == "__main__":
    run_all()
