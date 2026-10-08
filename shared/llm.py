"""
llm.py
======
Thin, optional LLM layer, following the same build_llm()/get_chat_model()
shape used in the Travel Planner reference project.

Design choice: the rule engine in rule_engine.py already produces a
correct, structured decision and a template rationale with NO API call
required. That keeps the pipeline runnable and gradeable offline
(no OPENAI_API_KEY needed) and keeps the review step grounded in fixed
facts rather than an LLM's guess.

The LLM is layered on top *only* to restate that structured result in
smoother natural language for the "Rationale" / critique text — it is
never asked to invent the status, payable amount, or flags. If no
OPENAI_API_KEY is set, or the `openai` package is not installed, every
function below silently falls back to the template text it was given,
so both crewai_healthclaim and langgraph_healthclaim run end-to-end
either way.
"""

from __future__ import annotations

import os
from typing import Optional


def _api_key_available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def build_llm(model: str = "gpt-4o-mini", temperature: float = 0.2):
    """Returns a LangChain-compatible chat model for LangGraph, or None if
    no API key / dependency is available (callers must handle None)."""
    if not _api_key_available():
        return None
    try:
        from langchain_openai import ChatOpenAI  # type: ignore
        return ChatOpenAI(model=model, temperature=temperature)
    except ImportError:
        return None


def get_chat_model(model: str = "gpt-4o-mini", temperature: float = 0.2):
    """Returns a plain OpenAI client + model name tuple for CrewAI's LLM
    config, or None if no API key / dependency is available."""
    if not _api_key_available():
        return None
    try:
        from crewai import LLM  # type: ignore
        return LLM(model=f"openai/{model}", temperature=temperature)
    except ImportError:
        return None


def polish_text(llm, prompt: str, fallback_text: str) -> str:
    """Ask the LLM to rewrite/polish fallback_text per prompt. Falls back
    to the template text untouched if no LLM is available or the call
    fails for any reason (network, quota, etc.) so the pipeline never
    breaks on the narration step."""
    if llm is None:
        return fallback_text
    try:
        # Works for both a LangChain chat model (.invoke) and CrewAI's LLM
        # (.call) — try the common interfaces defensively.
        full_prompt = f"{prompt}\n\nStructured facts (do not contradict these):\n{fallback_text}"
        if hasattr(llm, "invoke"):
            result = llm.invoke(full_prompt)
            return getattr(result, "content", str(result)) or fallback_text
        if hasattr(llm, "call"):
            return llm.call(full_prompt) or fallback_text
    except Exception:
        pass
    return fallback_text
