"""
main.py — CrewAI HealthClaim AI
================================
Runs every case in data/health_sample_test_inputs.json through the
3-agent, Process.sequential crew and prints a formatted decision report
for each.

Usage:
    cd crewai_healthclaim
    pip install -r requirements.txt   # crewai (+ its own OpenAI dependency)
    cp .env.example .env              # add a real OPENAI_API_KEY to run the real agents
    python main.py

Without an OPENAI_API_KEY, this runs the offline rule-engine fallback
described in src/crew.py so the pipeline is still fully exercisable and
produces a correct, structured decision for every case.
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

from src.crew import run_claim_through_crew


def run_all():
    store = get_default_store()
    test_cases = store.load_sample_test_inputs()

    summary = []
    for case in test_cases:
        state = run_claim_through_crew(case["claim"])
        decision = ClaimDecision(**state.final_decision)

        print(f"--- {case['id']}: {case['description']} ---")
        print(decision.format_report(case["claim"]["claim_id"]))
        print()

        summary.append((case["id"], decision.status, decision.verdict))

    print("=== Summary ===")
    for case_id, status, verdict in summary:
        print(f"{case_id}: status={status:<22} verdict={verdict}")

    revised_cases = [c for c in summary if c[2] == "REVISE"]
    print(f"\n{len(revised_cases)} of {len(summary)} cases had a draft that Agent 3 had to "
          f"correct: {[c[0] for c in revised_cases]}")
    print(
        "\nNote: CrewAI's Process.sequential cannot loop, so 'REVISE' here means Agent 3 "
        "caught and fixed the draft in its single pass, not a second trip through Agent 2 "
        "— see the LangGraph version for the genuine review<->revise loop."
    )


if __name__ == "__main__":
    run_all()
