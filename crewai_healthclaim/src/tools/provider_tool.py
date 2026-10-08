"""
provider_tool.py
================
Tool 2 of 4: provider network/fraud lookup by provider_name.
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


def _lookup_provider(provider_name: str) -> Optional[Dict[str, Any]]:
    """Fetch the provider's network/fraud record, or None if unrecognized."""
    return get_default_store().get_provider(provider_name)


lookup_provider = (
    _crewai_tool("lookup_provider")(_lookup_provider) if _crewai_tool else _lookup_provider
)
