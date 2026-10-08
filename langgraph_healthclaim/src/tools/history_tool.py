"""
history_tool.py
================
Tool 3 of 4: prior-claims lookup by member_id, backed by
health_claim_history.json. Used by review_decision (via full_triage) to
detect duplicate/suspicious resubmissions.
"""

import os
import sys
from typing import Any, Dict, List

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.data_loader import get_default_store  # noqa: E402

try:
    from langchain_core.tools import tool as _lc_tool
except ImportError:  # pragma: no cover - optional dependency
    _lc_tool = None


def _lookup_claim_history(member_id: str) -> List[Dict[str, Any]]:
    """Fetch prior claims for a member_id (empty list if none on file)."""
    return get_default_store().get_claim_history(member_id)


lookup_claim_history = _lc_tool(_lookup_claim_history) if _lc_tool else _lookup_claim_history
