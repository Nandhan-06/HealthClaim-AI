# HealthClaim AI — LangGraph version

A 4-node LangGraph `StateGraph` with 1 conditional edge that triages a raw
health insurance claim into a decision (`approved` / `rejected` /
`pending_documents` / `pending_investigation`), and genuinely loops a bad
draft decision back for correction.

## Structure

```
langgraph_healthclaim/
├── src/
│   ├── state.py          # ClaimState — the TypedDict every node reads/writes
│   ├── tools/             # the 4 data lookups, as LangChain tools
│   │   ├── policy_tool.py
│   │   ├── provider_tool.py
│   │   ├── history_tool.py
│   │   └── diagnosis_tool.py
│   ├── nodes/              # the 4 graph nodes
│   │   ├── intake_node.py    # Node 1: raw claim -> ClaimRequest
│   │   ├── triage_node.py    # Node 2: draft ClaimDecision (naive rule set)
│   │   ├── review_node.py    # Node 3: checks draft against ground truth
│   │   └── revise_node.py    # Node 4: applies the correction
│   ├── edges/
│   │   └── route_after_review.py   # the 1 conditional edge
│   └── graph.py             # wires the nodes + edge into a StateGraph
├── main.py                 # runs all 10 sample cases, prints reports
├── requirements.txt
└── .env.example
```

The core rule logic (`naive_triage`, `full_triage`, `review_decision`,
`revise_decision`) lives in `../shared/rule_engine.py` and is shared with
the CrewAI version — only the graph wiring and node/tool wrappers here
are LangGraph-specific.

## How to run

```bash
cd langgraph_healthclaim
pip install -r requirements.txt
cp .env.example .env   # optional — add a real OPENAI_API_KEY to polish rationale text
python main.py
```

No API key is required to get correct results: the triage/review/revise
logic is a deterministic, data-grounded rule engine (see
`shared/rule_engine.py`), so all 10 sample cases run and produce a
correct decision offline. An `OPENAI_API_KEY`, if set, is only used by
`shared/llm.py` to rewrite the rationale/critique text in smoother
language — it never re-decides the status, payable amount, or flags.

## The loop, concretely

`review_decision` compares the current decision against
`full_triage()` (ground truth built from the real policy/provider/
history/diagnosis data). If they disagree, `route_after_review` sends
the state to `revise_decision`, which adopts the corrected decision and
loops back to `review_decision` — capped by `max_iterations` (default 3)
so a stubborn claim can't loop forever.

Running `main.py` shows **TC02, TC03, TC05, TC08 and TC09** each fire at
least one REVISE loop (waiting-period + missing pre-auth, room-rent cap,
duplicate claim, fraud-flagged provider, and medical-necessity mismatch,
respectively) — the naive first-draft rule set in `triage_claim`
deliberately skips exactly those checks so the reviewer has something
real to catch.

## What I'd improve with more time

Expose the review step as a genuine LLM critique (an agent reasoning in
free text over the retrieved records, cross-checked against the rule
engine as a guardrail) rather than a pure rule-vs-rule diff, so it could
also catch issues outside the fixed rule set — e.g. a rationale that
sounds off given the documents actually submitted, or a request whose
combination of diagnosis and procedure code is technically in the map
but clinically implausible for the given claim amount.
