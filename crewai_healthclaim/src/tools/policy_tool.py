"""
policy_tool.py
==============
Tool 1 of 4, exposed as a real CrewAI @tool (stretch goal) when the
`crewai` package is available for Agent 2 / triage_claim to call, and as
a plain function either way so the fallback rule engine can call it
directly without the framework.
"""

import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.data_loader import get_default_store  # noqa: E402

try:
    from crewai.tools import tool as _crewai_tool
except ImportError:  # pragma: no cover - optional dependency
    _crewai_tool = None


def _lookup_policy(policy_number: str) -> Optional[Dict[str, Any]]:
    """Fetch the policy record for a given policy_number, or None if it
    does not exist in health_policies.json."""
    return get_default_store().get_policy(policy_number)


lookup_policy = (
    _crewai_tool("lookup_policy")(_lookup_policy) if _crewai_tool else _lookup_policy
)
