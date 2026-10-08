"""
agents.py
=========
The 3 CrewAI Agents for Process.sequential. Note the deliberate design
difference from the LangGraph version: Agent 3 both critiques AND fixes
the decision in a single pass, because a sequential pipeline can't loop
back to an earlier step the way a StateGraph can.

Building these requires the `crewai` package and (for a real run) an
OPENAI_API_KEY — see shared/llm.py for how the LLM is obtained and why
it's optional for getting a *correct* answer.
"""

import os
import sys

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..")))
from shared.llm import get_chat_model  # noqa: E402

from .tools import lookup_policy, lookup_provider, lookup_claim_history, lookup_allowed_procedures

try:
    from crewai import Agent
except ImportError:  # pragma: no cover - optional dependency
    Agent = None


def build_agents():
    """Returns (intake_agent, triage_agent, review_and_fix_agent). Requires
    the `crewai` package to be installed; raises ImportError otherwise
    (main.py falls back to the pure rule-engine simulation in that case)."""
    if Agent is None:
        raise ImportError("crewai is not installed — run `pip install crewai` to use real agents.")

    llm = get_chat_model()

    intake_agent = Agent(
        role="Claims Intake Analyst",
        goal=(
            "Read the raw claim submission and turn it into a clean, "
            "structured ClaimRequest with every field normalized."
        ),
        backstory=(
            "A meticulous former hospital records clerk who has seen every "
            "way a claim form can be filled in inconsistently, and never "
            "lets a malformed field slip through to the triage stage."
        ),
        tools=[],
        llm=llm,
        verbose=True,
    )

    triage_agent = Agent(
        role="Claims Triage Specialist",
        goal=(
            "Use the policy, provider, claim-history and diagnosis-procedure "
            "tools to run the rule engine and produce a draft ClaimDecision "
            "with a status, itemized payable amount, and rationale."
        ),
        backstory=(
            "A claims adjuster who grounds every decision in the actual "
            "policy and provider records rather than guessing at coverage "
            "rules from memory."
        ),
        tools=[lookup_policy, lookup_provider, lookup_claim_history, lookup_allowed_procedures],
        llm=llm,
        verbose=True,
    )

    review_and_fix_agent = Agent(
        role="Senior Claims Reviewer",
        goal=(
            "Critique the draft ClaimDecision against the actually retrieved "
            "policy/provider/history/diagnosis data — catching a payable "
            "amount that ignores the room-rent cap, a missed fraud or "
            "duplicate signal, or a procedure not justified by the "
            "diagnosis — and correct it in the same pass, since this "
            "pipeline has no separate revise step to loop back to."
        ),
        backstory=(
            "A skeptical senior reviewer who has been burned before by "
            "trusting a first-draft decision, and always re-derives the "
            "numbers from the source records before signing off."
        ),
        tools=[lookup_policy, lookup_provider, lookup_claim_history, lookup_allowed_procedures],
        llm=llm,
        verbose=True,
    )

    return intake_agent, triage_agent, review_and_fix_agent
