"""
shared
======
Framework-agnostic core used by BOTH the CrewAI and LangGraph implementations
of HealthClaim AI: the data models, the JSON data loader, the deterministic
rule engine (intake / triage / review / revise logic), and an optional LLM
wrapper for turning structured results into natural-language rationale.

Neither `crewai_healthclaim` nor `langgraph_healthclaim` duplicate this
logic — their nodes/agents/tools import from here and add the
orchestration (StateGraph vs. Process.sequential) on top.
"""
