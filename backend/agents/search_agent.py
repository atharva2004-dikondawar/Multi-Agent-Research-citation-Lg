"""
search_agent.py
---------------
Search Agent — Academic Source Finder (deterministic execution)

No LLM call here by design — this is what keeps free-tier LLM usage
low. Executes each query against Exa first, falls back to Tavily on
error/thin results, then dedups by URL across all queries.
"""
import json
import logging
from typing import List, Dict, Any

from backend.tools.search_tool import ExaSearchTool, TavilySearchTool

logger = logging.getLogger(__name__)

_exa = ExaSearchTool()
_tavily = TavilySearchTool()


def _search_one_query(query: str) -> List[Dict[str, Any]]:
    raw = _exa._run(query=query, num_results=8)
    results = json.loads(raw)

    if isinstance(results, dict) and results.get("error"):
        logger.warning("Exa error for '%s': %s — falling back to Tavily", query, results["error"])
        results = []

    if len(results) < 3:
        logger.info("Exa returned %d results for '%s' — supplementing with Tavily", len(results), query)
        raw_fallback = _tavily._run(query=query, num_results=8)
        fallback_results = json.loads(raw_fallback)
        if isinstance(fallback_results, list):
            results += fallback_results

    return results


def run_search_agent(queries: List[str]) -> List[Dict[str, Any]]:
    seen_urls = set()
    merged: List[Dict[str, Any]] = []

    for query in queries:
        try:
            results = _search_one_query(query)
        except Exception as exc:
            logger.error("Search failed for query '%s': %s", query, exc)
            continue

        for item in results:
            url = item.get("url")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            merged.append(item)

    logger.info("Search agent collected %d unique sources across %d queries", len(merged), len(queries))
    return merged