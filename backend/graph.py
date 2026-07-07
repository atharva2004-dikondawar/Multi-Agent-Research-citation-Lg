"""
graph.py
--------
Wires the 5 pipeline nodes into a LangGraph StateGraph.

Pipeline (identical linear order to the original CrewAI Process.sequential):
    planner -> search -> validator -> extractor -> synthesizer

Only planner, validator, and synthesizer make LLM calls (1 each).
search and the fetch-half of extractor are deterministic Python.
"""
import logging
from functools import partial

from langgraph.graph import StateGraph, END

from backend.graph_state import GraphState
from backend.llm import build_llm
from backend.tasks.planning_task import planning_node
from backend.tasks.search_task import search_node
from backend.tasks.validation_task import validation_node
from backend.tasks.extraction_task import extraction_node
from backend.tasks.summary_task import summary_node

logger = logging.getLogger(__name__)


def build_graph():
    llm = build_llm()

    graph = StateGraph(GraphState)

    # Bind the shared llm instance into the 3 nodes that need it
    graph.add_node("planner", partial(planning_node, llm=llm))
    graph.add_node("search", search_node)  # no llm — deterministic
    graph.add_node("validator", partial(validation_node, llm=llm))
    graph.add_node("extractor", partial(extraction_node, llm=llm))
    graph.add_node("synthesizer", partial(summary_node, llm=llm))

    graph.set_entry_point("planner")
    graph.add_edge("planner", "search")
    graph.add_edge("search", "validator")
    graph.add_edge("validator", "extractor")
    graph.add_edge("extractor", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()


# Node name -> human-readable progress label, used by app.py for SSE events
NODE_LABELS = {
    "planner": "Decomposing topic into queries…",
    "search": "Retrieving sources from Exa/Tavily…",
    "validator": "Scoring and filtering top sources…",
    "extractor": "Extracting technical evidence…",
    "synthesizer": "Writing final research report…",
}