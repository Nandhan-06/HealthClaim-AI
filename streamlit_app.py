"""
streamlit_app.py — HealthClaim AI UI
=====================================
A Streamlit front-end over the existing HealthClaim AI pipelines
(langgraph_healthclaim and crewai_healthclaim). No changes were made to
any existing project code — this file only imports and calls it.

Run:
    pip install streamlit langgraph langchain-core
    streamlit run streamlit_app.py
"""

import copy
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.data_loader import get_default_store
from shared.models import ClaimDecision

st.set_page_config(page_title="HealthClaim AI", page_icon="🩺", layout="wide")

STORE = get_default_store()
SAMPLE_CASES = STORE.load_sample_test_inputs()

STATUS_COLOR = {
    "approved": "🟢",
    "rejected": "🔴",
    "pending_documents": "🟡",
    "pending_investigation": "🟠",
}


# --------------------------------------------------------------------------
# Lazy, cached access to each implementation. Import errors (missing
# optional package like `langgraph` or `crewai`) are caught and surfaced
# in the UI instead of crashing the app.
# --------------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def get_langgraph_app():
    from langgraph_healthclaim.src.graph import build_graph
    return build_graph()


def run_langgraph(raw_claim):
    graph = get_langgraph_app()
    result = graph.invoke({"raw_claim": raw_claim})
    final = result.get("final_decision") or result.get("revised_decision") or result["draft_decision"]
    decision = ClaimDecision(**final)
    return decision, {"iterations": result.get("iteration", 0)}


def run_crewai(raw_claim):
    from crewai_healthclaim.src.crew import run_claim_through_crew
    state = run_claim_through_crew(raw_claim)
    decision = ClaimDecision(**state.final_decision)
    return decision, {}


IMPLEMENTATIONS = {
    "LangGraph (4-node state machine, real review↔revise loop)": run_langgraph,
    "CrewAI (3-agent sequential pipeline)": run_crewai,
}


# --------------------------------------------------------------------------
# Rendering helpers
# --------------------------------------------------------------------------

def render_decision(decision: ClaimDecision, claim_id: str, extra: dict):
    emoji = STATUS_COLOR.get(decision.status, "⚪")
    c1, c2, c3 = st.columns(3)
    c1.metric("Status", f"{emoji} {decision.status.upper()}")
    c2.metric("Payable Amount", f"Rs {decision.payable_amount:,.0f}")
    c3.metric("Verdict", decision.verdict)
    if "iterations" in extra:
        st.caption(f"Revision loops used: {extra['iterations']}")

    if decision.deductions:
        st.write("**Deductions**")
        st.table(
            {
                "Deduction": [k.replace("_", " ").title() for k in decision.deductions],
                "Amount (Rs)": [f"{v:,.0f}" for v in decision.deductions.values()],
            }
        )

    st.write("**Rationale**")
    st.write(decision.rationale or "_(none)_")

    if decision.flags:
        st.write("**Flags**")
        for f in decision.flags:
            st.markdown(f"- ⚠️ {f}")
    else:
        st.write("**Flags:** _(none)_")


def build_claim_form():
    """Custom-claim input form, defaulting to TC01's values."""
    default = SAMPLE_CASES[0]["claim"]
    diag_options = list(STORE.diagnosis_procedure_map.keys())

    with st.form("claim_form"):
        col1, col2 = st.columns(2)
        with col1:
            claim_id = st.text_input("Claim ID", value=default["claim_id"])
            member_id = st.text_input("Member ID", value=default["member_id"])
            policy_number = st.selectbox(
                "Policy Number", options=list(STORE.policies.keys()),
                index=list(STORE.policies.keys()).index(default["policy_number"])
                if default["policy_number"] in STORE.policies else 0,
            )
            diagnosis_code = st.selectbox(
                "Diagnosis Code", options=diag_options,
                index=diag_options.index(default["diagnosis_code"])
                if default["diagnosis_code"] in diag_options else 0,
            )
            proc_options = STORE.get_allowed_procedures(diagnosis_code) or ["PR-OTHER"]
            procedure_code = st.selectbox("Procedure Code", options=proc_options)
            claim_type = st.selectbox(
                "Claim Type", options=["cashless", "reimbursement"],
                index=["cashless", "reimbursement"].index(default["claim_type"]),
            )
            admission_type = st.selectbox(
                "Admission Type", options=["emergency", "planned"],
                index=["emergency", "planned"].index(default["admission_type"]),
            )
        with col2:
            provider_name = st.selectbox(
                "Provider", options=list(STORE.providers.keys()),
                index=list(STORE.providers.keys()).index(default["provider_name"])
                if default["provider_name"] in STORE.providers else 0,
            )
            date_of_admission = st.text_input("Date of Admission (YYYY-MM-DD)", value=default["date_of_admission"])
            date_of_discharge = st.text_input("Date of Discharge (YYYY-MM-DD)", value=default["date_of_discharge"])
            claim_amount_requested = st.number_input(
                "Claim Amount Requested (Rs)", min_value=0.0, value=float(default["claim_amount_requested"]), step=1000.0
            )
            room_rent_per_day = st.number_input(
                "Room Rent per Day (Rs)", min_value=0.0, value=float(default["room_rent_per_day"]), step=100.0
            )
            documents_submitted = st.multiselect(
                "Documents Submitted",
                options=["discharge_summary", "bills", "prescription", "pre_auth_letter", "id_proof"],
                default=default.get("documents_submitted", []),
            )

        submitted = st.form_submit_button("Run Triage", type="primary", use_container_width=True)

    if not submitted:
        return None

    return {
        "claim_id": claim_id,
        "member_id": member_id,
        "policy_number": policy_number,
        "diagnosis_code": diagnosis_code,
        "procedure_code": procedure_code,
        "claim_type": claim_type,
        "admission_type": admission_type,
        "provider_name": provider_name,
        "date_of_admission": date_of_admission,
        "date_of_discharge": date_of_discharge,
        "claim_amount_requested": claim_amount_requested,
        "room_rent_per_day": room_rent_per_day,
        "documents_submitted": documents_submitted,
    }


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------

st.sidebar.title("🩺 HealthClaim AI")
st.sidebar.caption(
    "All policy numbers, providers, member data, and rules are fictional — "
    "a simulation for practicing agentic design patterns."
)
impl_name = st.sidebar.radio("Implementation", list(IMPLEMENTATIONS.keys()))
impl_fn = IMPLEMENTATIONS[impl_name]

st.sidebar.divider()
st.sidebar.markdown(
    "**Note:** LangGraph needs the `langgraph` / `langchain-core` packages "
    "installed. CrewAI runs its offline rule-engine fallback automatically "
    "when `crewai` isn't installed or no `OPENAI_API_KEY` is set — either "
    "way it produces a correct, structured decision."
)

st.title("HealthClaim AI — Claims Triage")

tab_single, tab_batch = st.tabs(["Single Claim", "Batch — All Sample Cases"])

# --------------------------------------------------------------------------
# Tab 1: single claim (sample or custom)
# --------------------------------------------------------------------------
with tab_single:
    mode = st.radio("Claim source", ["Pick a sample case", "Enter a custom claim"], horizontal=True)

    raw_claim = None
    if mode == "Pick a sample case":
        case_labels = [f"{c['id']} — {c['description']}" for c in SAMPLE_CASES]
        chosen = st.selectbox("Sample case", case_labels)
        case = SAMPLE_CASES[case_labels.index(chosen)]
        st.json(case["claim"], expanded=False)
        if st.button("Run Triage", type="primary"):
            raw_claim = copy.deepcopy(case["claim"])
    else:
        raw_claim = build_claim_form()

    if raw_claim:
        try:
            with st.spinner(f"Running {impl_name.split(' (')[0]} pipeline..."):
                decision, extra = impl_fn(raw_claim)
        except ModuleNotFoundError as exc:
            st.error(
                f"Missing package for this implementation: `{exc.name}`. "
                f"Install it (see the sidebar note) and rerun."
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Pipeline failed: {exc}")
        else:
            st.divider()
            render_decision(decision, raw_claim["claim_id"], extra)

# --------------------------------------------------------------------------
# Tab 2: batch run over all 10 sample cases
# --------------------------------------------------------------------------
with tab_batch:
    st.write(f"Runs all {len(SAMPLE_CASES)} sample cases through **{impl_name}**.")
    if st.button("Run all sample cases", type="primary"):
        rows = []
        details = []
        progress = st.progress(0.0)
        try:
            for i, case in enumerate(SAMPLE_CASES):
                decision, extra = impl_fn(copy.deepcopy(case["claim"]))
                rows.append(
                    {
                        "Case": case["id"],
                        "Description": case["description"],
                        "Status": decision.status,
                        "Payable (Rs)": f"{decision.payable_amount:,.0f}",
                        "Verdict": decision.verdict,
                        "Revise loops": extra.get("iterations", "—"),
                    }
                )
                details.append((case, decision, extra))
                progress.progress((i + 1) / len(SAMPLE_CASES))
        except ModuleNotFoundError as exc:
            st.error(f"Missing package for this implementation: `{exc.name}`.")
        else:
            st.dataframe(rows, use_container_width=True, hide_index=True)
            revised = [r["Case"] for r in rows if r["Verdict"] == "REVISE"]
            st.caption(f"{len(revised)} of {len(rows)} cases required a correction: {revised}")

            for case, decision, extra in details:
                with st.expander(f"{case['id']} — {case['description']}"):
                    render_decision(decision, case["claim"]["claim_id"], extra)
