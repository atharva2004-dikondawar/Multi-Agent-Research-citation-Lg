"""
planning_task.py
----------------
Task logic for the Planner node. One LLM call: build the instruction,
invoke the LLM, parse the query list into state.
"""
import logging

from backend.agents.planner_agent import PLANNER_SYSTEM_PROMPT
from backend.llm import safe_invoke
from backend.parsing import parse_json_response

logger = logging.getLogger(__name__)


def _build_instruction(topic: str) -> str:
    return f"""TOPIC: {topic}

Decompose this topic into exactly 4-6 highly specific, actionable search queries. Each query should:
- Target a distinct sub-aspect (foundation, key methods, benchmarks, recent advances, open problems, applications)
- Be a natural-language string suited to arXiv, Semantic Scholar, IEEE Xplore, ACL Anthology, or GitHub search
- Avoid repetition — each query covers unique ground

Do NOT perform any web searches. Return ONLY this JSON object, no prose, no markdown fences:
{{"queries": ["query1", "query2", ...]}}"""


def planning_node(state: dict, llm) -> dict:
    topic = state["topic"]
    logger.info("Planner: decomposing topic '%s'", topic)

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
        {"role": "user", "content": _build_instruction(topic)},
    ]
    raw = safe_invoke(llm, messages)
    parsed = parse_json_response(raw)
    queries = parsed.get("queries", [])

    if not queries:
        logger.warning("Planner returned no queries; falling back to topic as a single query.")
        queries = [topic]

    logger.info("Planner produced %d queries", len(queries))
    return {"queries": queries}