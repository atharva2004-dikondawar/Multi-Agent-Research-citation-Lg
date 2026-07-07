"""
search_task.py
--------------
Task wrapper for the Search node. No LLM call — purely orchestrates
the deterministic Search Agent and updates graph state.
"""
import logging

from backend.agents.search_agent import run_search_agent

logger = logging.getLogger(__name__)


def search_node(state: dict) -> dict:
    queries = state.get("queries", [])
    raw_sources = run_search_agent(queries)
    return {"raw_sources": raw_sources}