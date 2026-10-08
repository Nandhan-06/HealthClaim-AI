"""
rule_engine.py
==============
The grounded, testable "brain" behind triage_claim / review_decision /
revise_decision. Kept deterministic (no LLM call required to get a
correct answer) so that:

  1. The 10 sample cases can be run and graded without an API key.
  2. The review step has a real, fixed set of facts to check the draft
     decision against (per the assignment: "keeps triage grounded in a
     fixed, known set of facts and makes the rule logic testable").

Both the CrewAI agents and the LangGraph nodes call these same
functions — an LLM (see shared/llm.py) is layered on top only to turn
the structured result into natural-language rationale/critique text,
never to re-decide the numbers.

Two triage passes are exposed on purpose:

  naive_triage()  — the "first draft" rule set. It intentionally skips
                     the harder checks (medical necessity, waiting
                     period / pre-auth, provider fraud/network signal,
                     duplicate-claim detection, room-rent cap) so that
                     review_decision has real problems to catch, per
                     TC02, TC03, TC05, TC08 and TC09.

  full_triage()   — the complete, correct rule set. review_decision
                     uses it as ground truth to flag a draft; when a
                     REVISE fires, revise_decision adopts this result
                     as the corrected decision.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Tuple

from .models import ClaimDecision
from .data_loader import DataStore

REQUIRED_DOCS = ["discharge_summary", "bills"]
DUPLICATE_WINDOW_DAYS = 7
MAX_ITERATIONS = 3


def _parse_date(d: str) -> datetime.date:
    return datetime.date.fromisoformat(d)


def _months_between(earlier: datetime.date, later: datetime.date) -> int:
    months = (later.year - earlier.year) * 12 + (later.month - earlier.month)
    if later.day < earlier.day:
        months -= 1
    return months


def _copay_pct(policy: Dict[str, Any], provider: Optional[Dict[str, Any]]) -> float:
    in_network = bool(provider and provider.get("network") == "in_network")
    return policy["network_copay_pct"] if in_network else policy["out_of_network_copay_pct"]


# ---------------------------------------------------------------------------
# Draft (naive) triage — Node 2 / Agent 2, first pass
# ---------------------------------------------------------------------------

def naive_triage(claim: Dict[str, Any], store: DataStore) -> ClaimDecision:
    """The deliberately-incomplete first-draft rule engine. Handles the
    'obvious' terminal cases correctly (lapsed policy, excluded condition,
    missing documents) but skips medical-necessity, waiting-period/pre-auth,
    fraud/network, duplicate-claim and room-rent-cap checks — exactly the
    gaps review_decision exists to catch."""

    policy = store.get_policy(claim["policy_number"])
    provider = store.get_provider(claim["provider_name"])

    if not policy or policy.get("policy_status") != "active":
        return ClaimDecision(
            status="rejected", payable_amount=0, deductions={},
            rationale="Policy not found or not active.",
            flags=["policy_inactive"],
        )

    if claim["diagnosis_code"] in policy.get("excluded_conditions", []):
        return ClaimDecision(
            status="rejected", payable_amount=0, deductions={},
            rationale=f"Diagnosis {claim['diagnosis_code']} is an excluded condition under this policy.",
            flags=["excluded_condition"],
        )

    missing_docs = [d for d in REQUIRED_DOCS if d not in claim.get("documents_submitted", [])]
    if missing_docs:
        return ClaimDecision(
            status="pending_documents", payable_amount=0, deductions={},
            rationale=f"Missing required document(s): {missing_docs}.",
            flags=["missing_documents"],
        )

    copay_pct = _copay_pct(policy, provider)
    requested = claim["claim_amount_requested"]
    copay_deduction = round(requested * copay_pct / 100)
    payable = requested - copay_deduction

    remaining_si = policy["sum_insured"] - policy["sum_insured_used_ytd"]
    non_covered = 0.0
    if payable > remaining_si:
        non_covered = payable - remaining_si
        payable = remaining_si

    return ClaimDecision(
        status="approved",
        payable_amount=payable,
        deductions={"co_pay": copay_deduction, "room_rent_excess": 0, "non_covered": non_covered},
        rationale=f"Co-pay of {copay_pct}% applied based on provider network status.",
        flags=[],
    )


# ---------------------------------------------------------------------------
# Ground-truth (full) triage — used by review_decision to check the draft,
# and adopted by revise_decision as the corrected decision.
# ---------------------------------------------------------------------------

def full_triage(claim: Dict[str, Any], store: DataStore) -> ClaimDecision:
    """The complete rule set: everything naive_triage checks, plus
    medical necessity, waiting period (planned admissions only),
    pre-authorization, provider fraud/network signal, duplicate-claim
    detection, and the room-rent proportionate-deduction cap."""

    policy = store.get_policy(claim["policy_number"])
    provider = store.get_provider(claim["provider_name"])

    if not policy or policy.get("policy_status") != "active":
        return ClaimDecision(
            status="rejected", payable_amount=0, deductions={},
            rationale="Policy not found or not active.",
            flags=["policy_inactive"],
        )

    if claim["diagnosis_code"] in policy.get("excluded_conditions", []):
        return ClaimDecision(
            status="rejected", payable_amount=0, deductions={},
            rationale=f"Diagnosis {claim['diagnosis_code']} is an excluded condition under this policy.",
            flags=["excluded_condition"],
        )

    allowed_procedures = store.get_allowed_procedures(claim["diagnosis_code"])
    if claim["procedure_code"] not in allowed_procedures:
        return ClaimDecision(
            status="rejected", payable_amount=0, deductions={},
            rationale=(
                f"Procedure {claim['procedure_code']} is not medically justified "
                f"for diagnosis {claim['diagnosis_code']} (allowed: {allowed_procedures})."
            ),
            flags=["medical_necessity_mismatch"],
        )

    admission = _parse_date(claim["date_of_admission"])
    policy_start = _parse_date(policy["policy_start_date"])
    elapsed_months = _months_between(policy_start, admission)

    flags: List[str] = []
    # PED waiting period is only enforced for planned/elective admissions;
    # emergencies are not blocked on it.
    if claim.get("admission_type") == "planned" and elapsed_months < policy.get("ped_waiting_period_months", 0):
        flags.append("waiting_period_violation")

    if (
        claim["procedure_code"] in policy.get("pre_auth_required_procedures", [])
        and claim.get("admission_type") == "planned"
        and "pre_authorization" not in claim.get("documents_submitted", [])
    ):
        flags.append("missing_pre_auth")

    if "waiting_period_violation" in flags:
        return ClaimDecision(
            status="rejected", payable_amount=0, deductions={},
            rationale=(
                f"Waiting period for pre-existing conditions has not been cleared "
                f"({elapsed_months} of {policy['ped_waiting_period_months']} months elapsed)."
            ),
            flags=flags,
        )

    missing_docs = [d for d in REQUIRED_DOCS if d not in claim.get("documents_submitted", [])]
    if missing_docs or "missing_pre_auth" in flags:
        if missing_docs:
            flags.append("missing_documents")
        missing_desc = missing_docs + (["pre_authorization"] if "missing_pre_auth" in flags else [])
        return ClaimDecision(
            status="pending_documents", payable_amount=0, deductions={},
            rationale=f"Missing required document(s): {missing_desc}.",
            flags=flags,
        )

    if not provider:
        return ClaimDecision(
            status="pending_investigation", payable_amount=0, deductions={},
            rationale=f"Provider '{claim['provider_name']}' was not found in the provider database.",
            flags=["unknown_provider"],
        )

    if provider.get("fraud_flag"):
        return ClaimDecision(
            status="pending_investigation", payable_amount=0, deductions={},
            rationale=f"Provider {claim['provider_name']} carries an active fraud flag; routed for investigation.",
            flags=["fraud_signal"],
        )

    member_history = store.get_claim_history(claim["member_id"])
    for prior in member_history:
        if prior["procedure_code"] == claim["procedure_code"] and prior["status"] == "approved":
            gap_days = abs((admission - _parse_date(prior["date_of_service"])).days)
            if gap_days <= DUPLICATE_WINDOW_DAYS:
                return ClaimDecision(
                    status="pending_investigation", payable_amount=0, deductions={},
                    rationale=(
                        f"Possible duplicate of claim {prior['claim_id']} for the same "
                        f"procedure, submitted {gap_days} day(s) apart."
                    ),
                    flags=["duplicate_claim"],
                )

    copay_pct = _copay_pct(policy, provider)
    cap_per_day = policy["sum_insured"] * policy["room_rent_cap_pct_of_si_per_day"] / 100
    requested = claim["claim_amount_requested"]

    eligible = requested
    room_rent_deduction = 0.0
    if claim["room_rent_per_day"] > cap_per_day:
        ratio = cap_per_day / claim["room_rent_per_day"]
        eligible = round(requested * ratio)
        room_rent_deduction = requested - eligible

    copay_deduction = round(eligible * copay_pct / 100)
    payable = eligible - copay_deduction

    remaining_si = policy["sum_insured"] - policy["sum_insured_used_ytd"]
    non_covered = 0.0
    if payable > remaining_si:
        non_covered = payable - remaining_si
        payable = remaining_si

    rationale_parts = []
    if room_rent_deduction:
        rationale_parts.append(
            f"Room rent of Rs {claim['room_rent_per_day']:,.0f}/day exceeded the policy cap of "
            f"Rs {cap_per_day:,.0f}/day; a proportionate deduction was applied to the claim."
        )
    rationale_parts.append(f"Co-pay of {copay_pct}% applied based on {provider['network']} status.")
    if non_covered:
        rationale_parts.append("Remaining sum insured was insufficient to cover the full eligible amount.")

    return ClaimDecision(
        status="approved",
        payable_amount=payable,
        deductions={
            "co_pay": copay_deduction,
            "room_rent_excess": room_rent_deduction,
            "non_covered": non_covered,
        },
        rationale=" ".join(rationale_parts),
        flags=[],
    )


# ---------------------------------------------------------------------------
# review_decision — compares a draft decision against ground truth
# ---------------------------------------------------------------------------

def review_decision(
    claim: Dict[str, Any], draft: ClaimDecision, store: DataStore
) -> Tuple[str, List[str], ClaimDecision]:
    """Checks the draft decision against the full rule set. Returns
    (verdict, flags, ground_truth_decision). verdict is 'PASS' if the
    draft's status and payable amount already match ground truth,
    otherwise 'REVISE' with the specific flags that were missed."""

    ground_truth = full_triage(claim, store)

    # Structural mismatches are what actually determine PASS vs. REVISE —
    # once a draft's status and payable amount match ground truth, it PASSes
    # even though ground_truth.flags (e.g. "excluded_condition") may still
    # be non-empty; those are attached below purely for audit context.
    mismatches: List[str] = []
    if draft.status != ground_truth.status:
        mismatches.append(f"status_mismatch:draft={draft.status},expected={ground_truth.status}")
    if round(draft.payable_amount) != round(ground_truth.payable_amount):
        mismatches.append(
            f"payable_amount_mismatch:draft={draft.payable_amount:,.0f},"
            f"expected={ground_truth.payable_amount:,.0f}"
        )

    verdict = "PASS" if not mismatches else "REVISE"
    flags = mismatches + [f for f in ground_truth.flags if f not in mismatches]
    return verdict, flags, ground_truth


# ---------------------------------------------------------------------------
# revise_decision — adopts the ground-truth decision, carrying review flags
# ---------------------------------------------------------------------------

def revise_decision(
    ground_truth: ClaimDecision, review_flags: List[str]
) -> ClaimDecision:
    """Produces the corrected decision. In this rule-grounded design the
    correction *is* the full-rule-set result; what changes across a
    revision is that the review's flags are now attached to the record
    for auditability."""
    corrected = ClaimDecision(
        status=ground_truth.status,
        payable_amount=ground_truth.payable_amount,
        deductions=dict(ground_truth.deductions),
        rationale=ground_truth.rationale,
        flags=sorted(set(ground_truth.flags) | set(review_flags)),
    )
    return corrected


# ---------------------------------------------------------------------------
# Full review<->revise loop, capped at MAX_ITERATIONS — used by both
# the LangGraph conditional-edge graph and the CrewAI single-pass agent
# (which simply calls this with max_iterations=1 worth of correction
# baked into one agent, since CrewAI's sequential Process cannot loop).
# ---------------------------------------------------------------------------

def run_review_revise_loop(
    claim: Dict[str, Any],
    draft: ClaimDecision,
    store: DataStore,
    max_iterations: int = MAX_ITERATIONS,
) -> Tuple[ClaimDecision, int]:
    """Repeatedly reviews `draft`, revising it on REVISE, until it PASSes
    or max_iterations is hit. Returns (final_decision, iterations_used)."""

    current = draft
    iterations_used = 0
    for iteration in range(1, max_iterations + 1):
        verdict, flags, ground_truth = review_decision(claim, current, store)
        if verdict == "PASS":
            current.verdict = "PASS"
            return current, iterations_used
        current = revise_decision(ground_truth, flags)
        iterations_used = iteration
        # After adopting the ground-truth decision, re-review immediately;
        # if it still doesn't PASS (shouldn't happen with this rule set,
        # but the cap protects against a stubborn claim looping forever)
        # and we've hit the cap, stop and accept the corrected decision.
        recheck_verdict, _, _ = review_decision(claim, current, store)
        if recheck_verdict == "PASS" or iteration == max_iterations:
            current.verdict = "PASS"
            return current, iterations_used
    return current, iterations_used
