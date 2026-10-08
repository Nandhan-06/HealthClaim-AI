# HealthClaim AI — CrewAI version

A 3-agent `Process.sequential` crew that triages a raw health insurance
claim into a decision (`approved` / `rejected` / `pending_documents` /
`pending_investigation`).

## Structure

```
crewai_healthclaim/
├── src/
│   ├── state.py           # ClaimTriageState — the payload handed forward task to task
│   ├── tools/               # the 4 data lookups, as CrewAI @tool functions
│   │   ├── policy_tool.py
│   │   ├── provider_tool.py
│   │   ├── history_tool.py
│   │   └── diagnosis_tool.py
│   ├── agents.py            # the 3 Agents: intake, triage, review-and-fix
│   └── crew.py              # Tasks + Crew(Process.sequential) + offline fallback runner
├── main.py                  # runs all 10 sample cases, prints reports
├── requirements.txt
└── .env.example
```

The core rule logic (`naive_triage`, `full_triage`) lives in
`../shared/rule_engine.py` and is shared with the LangGraph version —
only the agent/task wiring and tool wrappers here are CrewAI-specific.

## The deliberate design difference from LangGraph

`Process.sequential` runs each task once, in order, and can't loop back
to an earlier step. So Agent 3 ("Senior Claims Reviewer") both critiques
**and** fixes the draft decision in a single pass — there's no separate
`revise_decision` task to hand off to, unlike the LangGraph version's
two-node `review_decision` / `revise_decision` split. This is the whole
teaching point of comparing the two frameworks, so it's preserved
deliberately rather than "fixed."

## How to run

```bash
cd crewai_healthclaim
pip install -r requirements.txt
cp .env.example .env   # add a real OPENAI_API_KEY to run the actual LLM-backed agents
python main.py
```

**With `OPENAI_API_KEY` set** (and `crewai` installed), `main.py` builds
and kicks off the real 3-agent crew from `src/agents.py` / `src/crew.py`.

**Without a key**, `run_claim_through_crew()` in `src/crew.py`
transparently falls back to calling the exact same shared tools and rule
engine the agents' tools wrap — same responsibilities (intake → triage →
review-and-fix), same data, no LLM call. This is what actually runs in
CI/offline and is why all 10 sample cases still produce a correct,
fully structured decision without a key.

## Sample results

Running `main.py`, **TC02, TC03, TC05, TC08 and TC09** each come back
with `Verdict: REVISE` — meaning Agent 3 caught and corrected something
the naive first-draft rule set in Agent 2 got wrong (waiting period +
missing pre-auth, room-rent cap, a duplicate claim, a fraud-flagged
provider, and a medical-necessity mismatch, respectively). The other 5
cases pass with `Verdict: PASS` on the first draft.

## What I'd improve with more time

- Add `output_pydantic=ClaimRequest` / `output_pydantic=ClaimDecision`
  to each `Task` in `src/crew.py` so the LLM's output is parsed and
  validated automatically instead of hand-parsed JSON.
- Turn the stretch-goal Appeals Handler into a 4th agent/task here too,
  to see how much harder it is to bolt on versus extending the
  LangGraph graph.
- Give Agent 3 a second, independent "self-check" tool call before
  finalizing, so the single-pass review-and-fix step gets at least one
  round of self-consistency checking even without a real loop.
