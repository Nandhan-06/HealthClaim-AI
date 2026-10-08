"""
data_loader.py
==============
Loads the four "tool" datasets (policies, providers, claim history,
diagnosis->procedure map) plus the sample test inputs into memory once,
and exposes simple lookup methods. Both `crewai_healthclaim/src/tools`
and `langgraph_healthclaim/src/tools` wrap these lookups as their
framework's own tool/function-calling interface — the data access
logic itself lives here exactly once.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

# Repo layout: <root>/data/*.json, <root>/{crewai,langgraph}_healthclaim/...
_DEFAULT_DATA_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data")
)


class DataStore:
    """Read-only, in-memory view over the four HealthClaim AI datasets."""

    def __init__(self, data_dir: Optional[str] = None):
        self.data_dir = data_dir or _DEFAULT_DATA_DIR
        self.policies: Dict[str, Any] = self._load("health_policies.json")
        self.providers: Dict[str, Any] = self._load("health_providers.json")
        self.claim_history: Dict[str, Any] = self._load("health_claim_history.json")
        self.diagnosis_procedure_map: Dict[str, Any] = self._load(
            "health_diagnosis_procedure_map.json"
        )

    def _load(self, filename: str) -> Any:
        path = os.path.join(self.data_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_sample_test_inputs(self) -> List[Dict[str, Any]]:
        path = os.path.join(self.data_dir, "health_sample_test_inputs.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ---- lookups (the four "tools") -------------------------------------

    def get_policy(self, policy_number: str) -> Optional[Dict[str, Any]]:
        """Tool 1: fetch the policy record by policy_number."""
        return self.policies.get(policy_number)

    def get_provider(self, provider_name: str) -> Optional[Dict[str, Any]]:
        """Tool 2: fetch the provider's network/fraud record by name."""
        return self.providers.get(provider_name)

    def get_claim_history(self, member_id: str) -> List[Dict[str, Any]]:
        """Tool 3: fetch prior claims for a member_id."""
        return self.claim_history.get(member_id, [])

    def get_allowed_procedures(self, diagnosis_code: str) -> List[str]:
        """Tool 4: fetch the medically-justified procedures for a diagnosis."""
        return self.diagnosis_procedure_map.get(diagnosis_code, [])


# A module-level singleton is convenient for both frameworks' tool wrappers,
# which are typically plain functions rather than classes with state.
_default_store: Optional[DataStore] = None


def get_default_store() -> DataStore:
    global _default_store
    if _default_store is None:
        _default_store = DataStore()
    return _default_store
