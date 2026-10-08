"""
history_tool.py
================
Tool 3 of 4: prior-claims lookup by member_id, used to flag duplicate
resubmissions.
"""

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.data_loader import get_default_store  # noqa: E402

try:
    from crewai.tools import tool as _crewai_tool
except ImportError:  # pragma: no cover - optional dependency
    _crewai_tool = None


def _lookup_claim_history(member_id: str) -> List[Dict[str, Any]]:
    """Fetch prior claims for a member_id (empty list if none on file)."""
    return get_default_store().get_claim_history(member_id)


lookup_claim_history = (
    _crewai_tool("lookup_claim_history")(_lookup_claim_history)
    if _crewai_tool else _lookup_claim_history
)
