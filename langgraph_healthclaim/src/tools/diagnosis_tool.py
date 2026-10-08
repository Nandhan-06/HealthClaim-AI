"""
diagnosis_tool.py
=================
Tool 4 of 4: medical-necessity lookup — which procedures are allowed for
a given diagnosis_code, backed by health_diagnosis_procedure_map.json.
"""

import os
import sys
from typing import List

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from shared.data_loader import get_default_store  # noqa: E402

try:
    from langchain_core.tools import tool as _lc_tool
except ImportError:  # pragma: no cover - optional dependency
    _lc_tool = None


def _lookup_allowed_procedures(diagnosis_code: str) -> List[str]:
    """Fetch the list of procedure codes considered medically justified
    for a diagnosis_code (empty list if the diagnosis is unmapped)."""
    return get_default_store().get_allowed_procedures(diagnosis_code)


lookup_allowed_procedures = _lc_tool(_lookup_allowed_procedures) if _lc_tool else _lookup_allowed_procedures
