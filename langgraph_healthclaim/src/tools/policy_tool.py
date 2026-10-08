"""
policy_tool.py
==============
Tool 1 of 4: policy lookup by policy_number, backed by health_policies.json
(via shared/data_loader.py). Exposed as a real LangChain tool when the
`langchain_core` package is available (stretch goal: "expose each lookup
as an actual tool function the agent calls"), and as a plain importable
function either way so triage_node can call it directly.
"""

import os
import sys
from typing import Any, Dict, Optional

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.data_loader import get_default_store  # noqa: E402

try:
    from langchain_core.tools import tool as _lc_tool
except ImportError:  # pragma: no cover - optional dependency
    _lc_tool = None


def _lookup_policy(policy_number: str) -> Optional[Dict[str, Any]]:
    """Fetch the policy record for a given policy_number, or None if it
    does not exist in health_policies.json."""
    return get_default_store().get_policy(policy_number)


lookup_policy = _lc_tool(_lookup_policy) if _lc_tool else _lookup_policy
