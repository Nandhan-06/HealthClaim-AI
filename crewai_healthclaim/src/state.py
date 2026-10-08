"""
state.py
========
CrewAI's Process.sequential has no explicit state object the way
LangGraph does — each task's output is simply passed forward as
`context=[...]` for the next task. To keep the same discipline anyway
(and make each task's output easy to inspect/log), this module defines
the structured payload each of the 3 agents hands off: a
"ClaimTriageState" that accumulates claim_request -> draft_decision ->
final_decision across the pipeline, mirroring LangGraph's ClaimState
but built up incrementally rather than mutated in place by a runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ClaimTriageState:
    raw_claim: Dict[str, Any]
    claim_request: Optional[Dict[str, Any]] = None
    draft_decision: Optional[Dict[str, Any]] = None
    review_flags: List[str] = field(default_factory=list)
    final_decision: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_claim": self.raw_claim,
            "claim_request": self.claim_request,
            "draft_decision": self.draft_decision,
            "review_flags": self.review_flags,
            "final_decision": self.final_decision,
        }
