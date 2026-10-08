"""
provider_tool.py
================
Tool 2 of 4: provider lookup by provider_name, backed by
health_providers.json (network status + fraud_flag).
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


def _lookup_provider(provider_name: str) -> Optional[Dict[str, Any]]:
    """Fetch the provider's network/fraud record, or None if the provider
    is not recognized in health_providers.json."""
    return get_default_store().get_provider(provider_name)


lookup_provider = _lc_tool(_lookup_provider) if _lc_tool else _lookup_provider
