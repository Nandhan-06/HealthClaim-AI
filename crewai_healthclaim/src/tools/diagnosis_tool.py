"""
diagnosis_tool.py
=================
Tool 4 of 4: medical-necessity lookup — allowed procedures per
diagnosis_code.
"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.data_loader import get_default_store  # noqa: E402

try:
    from crewai.tools import tool as _crewai_tool
except ImportError:  # pragma: no cover - optional dependency
    _crewai_tool = None


def _lookup_allowed_procedures(diagnosis_code: str) -> List[str]:
    """Fetch procedure codes considered medically justified for a diagnosis."""
    return get_default_store().get_allowed_procedures(diagnosis_code)


lookup_allowed_procedures = (
    _crewai_tool("lookup_allowed_procedures")(_lookup_allowed_procedures)
    if _crewai_tool else _lookup_allowed_procedures
)
