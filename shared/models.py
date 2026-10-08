"""
models.py
=========
The two structured objects that flow through both workflows:

  ClaimRequest  — produced by intake_claim (Node 1 / Agent 1)
  ClaimDecision — produced by triage_claim, checked by review_decision,
                  corrected by revise_decision (LangGraph), or produced
                  and fixed in one pass by Agent 3 (CrewAI)
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class ClaimRequest:
    """Clean, structured representation of a raw incoming claim."""

    claim_id: str
    member_id: str
    policy_number: str
    diagnosis_code: str
    procedure_code: str
    claim_type: str
    admission_type: str
    provider_name: str
    date_of_admission: str
    date_of_discharge: str
    claim_amount_requested: float
    room_rent_per_day: float
    documents_submitted: List[str] = field(default_factory=list)

    @classmethod
    def from_raw(cls, raw: Dict[str, Any]) -> "ClaimRequest":
        """Build a ClaimRequest from the raw claim dict, raising a clear
        error if a required field is missing rather than failing later
        with a KeyError deep inside the rule engine."""
        required = [
            "claim_id", "member_id", "policy_number", "diagnosis_code",
            "procedure_code", "claim_type", "admission_type", "provider_name",
            "date_of_admission", "date_of_discharge", "claim_amount_requested",
            "room_rent_per_day",
        ]
        missing = [f for f in required if f not in raw]
        if missing:
            raise ValueError(f"Raw claim is missing required field(s): {missing}")
        return cls(
            claim_id=raw["claim_id"],
            member_id=raw["member_id"],
            policy_number=raw["policy_number"],
            diagnosis_code=raw["diagnosis_code"],
            procedure_code=raw["procedure_code"],
            claim_type=raw["claim_type"],
            admission_type=raw["admission_type"],
            provider_name=raw["provider_name"],
            date_of_admission=raw["date_of_admission"],
            date_of_discharge=raw["date_of_discharge"],
            claim_amount_requested=raw["claim_amount_requested"],
            room_rent_per_day=raw["room_rent_per_day"],
            documents_submitted=list(raw.get("documents_submitted", [])),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ClaimDecision:
    """A triage decision at any stage (draft, revised, or final)."""

    status: str  # approved | rejected | pending_documents | pending_investigation
    payable_amount: float
    deductions: Dict[str, float] = field(default_factory=dict)
    rationale: str = ""
    flags: List[str] = field(default_factory=list)
    verdict: str = "PENDING"  # PASS | REVISE | PENDING (not yet reviewed)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def format_report(self, claim_id: str) -> str:
        lines = [
            f"Claim ID: {claim_id}",
            f"Status: {self.status.upper()}",
            f"Payable Amount: Rs {self.payable_amount:,.0f}",
            "Deductions:",
        ]
        if self.deductions:
            for label, amount in self.deductions.items():
                lines.append(f"  - {label.replace('_', ' ').title()}: Rs {amount:,.0f}")
        else:
            lines.append("  - (none)")
        lines.append(f"Rationale: {self.rationale}")
        lines.append(f"Flags: {self.flags}")
        lines.append(f"Verdict: {self.verdict}")
        return "\n".join(lines)
