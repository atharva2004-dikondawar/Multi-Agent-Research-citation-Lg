"""
graph_state.py
---------------
Shared state schema passed between all LangGraph nodes.
"""
from typing import TypedDict, List, Dict, Any


class GraphState(TypedDict, total=False):
    topic: str
    queries: List[str]
    raw_sources: List[Dict[str, Any]]
    validated_sources: List[Dict[str, Any]]
    evidence: List[Dict[str, Any]]
    report: str