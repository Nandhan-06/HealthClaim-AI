# HealthClaim AI

Same claims-triage workflow, built twice: once as a 3-agent CrewAI
sequential pipeline, once as a 4-node LangGraph state machine with a
genuine review ↔ revise loop.

> All policy numbers, providers, member data, and rules here are
> fictional — this is a simulation for practicing agentic design
> patterns, not real insurance guidance.

## Layout

```
HealthClaim_AI/
├── data/                        # the 5 provided datasets — single source of truth
│   ├── health_policies.json
│   ├── health_providers.json
│   ├── health_claim_history.json
│   ├── health_diagnosis_procedure_map.json
│   └── health_sample_test_inputs.json      # 10 sample cases
├── shared/                      # framework-agnostic core, used by BOTH implementations
│   ├── models.py                 # ClaimRequest, ClaimDecision
│   ├── data_loader.py             # loads data/*.json, exposes the 4 lookups
│   ├── rule_engine.py             # naive_triage / full_triage / review / revise / loop
│   └── llm.py                     # optional LLM narration layer (build_llm/get_chat_model)
├── langgraph_healthclaim/       # LangGraph version — src/{state, tools, nodes, edges, graph}.py
├── crewai_healthclaim/          # CrewAI version    — src/{state, tools, agents, crew}.py
├── run_all_tests.py             # runs both implementations' main.py, saves output/test_run_log.txt
└── output/
    └── test_run_log.txt          # saved console output for all 10 cases x both implementations
```

Each implementation folder is a standalone, runnable project (own
`main.py`, `requirements.txt`, `.env.example`, `README.md`) — see those
READMEs for how to run each one individually. `data/` and `shared/` are
the one shared source of truth so the two implementations can't drift
apart on facts or rules; only the orchestration (`Process.sequential`
vs. `StateGraph`) differs between them.

## Quick start

```bash
python run_all_tests.py
```

This runs all 10 sample cases through both implementations and writes
`output/test_run_log.txt`. No `OPENAI_API_KEY` is required to get
correct results — see "How the LLM fits in" below.

## The design, in one paragraph

`shared/rule_engine.py` has two triage passes: `naive_triage()` (the
"first draft" — deliberately skips medical-necessity, waiting-period/
pre-auth, provider fraud/network, duplicate-claim, and room-rent-cap
checks) and `full_triage()` (the complete, correct rule set, built from
the same 4 data-lookup tools). `review_decision()` compares a draft
against `full_triage()`'s ground truth; when they disagree, that's a
real, data-grounded flaw — not a simulated one. In LangGraph this drives
an actual conditional edge (`route_after_review`) that loops back to a
`revise_decision` node, capped by `max_iterations`. In CrewAI, since
`Process.sequential` can't loop, Agent 3 does the review-and-fix in one
combined pass instead.

Running the 10 sample cases, **TC02, TC03, TC05, TC08, and TC09** each
trip at least one revision — waiting period + missing pre-auth, room-rent
cap overrun, a duplicate claim submitted a day apart, a fraud-flagged
provider, and a procedure not justified by the diagnosis, respectively.
The other 5 cases pass on the first draft.

## How the LLM fits in

The rule engine never depends on an LLM to get a *correct* answer — that
keeps the pipeline gradeable offline and keeps review grounded in fixed
facts rather than an LLM's guess. `shared/llm.py` (mirroring the
Travel Planner reference project's `build_llm()` / `get_chat_model()`
pattern) is layered on top only to restate the structured result in
smoother natural language for the rationale/critique text. Set a real
`OPENAI_API_KEY` in either implementation's `.env` to use it; without
one, both implementations fall back to the template rationale text and
still run end-to-end.

## What I'd improve with more time

- Wire `Task(output_pydantic=ClaimDecision)` into the real CrewAI tasks
  (`crewai_healthclaim/src/crew.py`) so the LLM's JSON output is parsed
  and validated directly instead of documenting it as a follow-up.
- Add the Appeals Handler stretch goal as a genuine extension of the
  LangGraph graph (a 5th node reachable from a member-appeal input),
  to prove the graph is actually extensible after the fact.
- Move the fixed thresholds in `rule_engine.py` (the 7-day duplicate
  window, the required-documents list) into `data/` alongside the other
  four datasets, so tuning them doesn't require a code change.
