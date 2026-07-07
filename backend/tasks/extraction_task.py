"""
extraction_task.py
------------------
Task logic for the Extractor node.

Step 1 (deterministic): fetch content for every validated source.
Step 2 (single batched LLM call): extract structured evidence for
ALL sources in one shot, respecting the 300-token-per-source budget.
"""
import logging

from backend.agents.extractor_agent import EXTRACTOR_SYSTEM_PROMPT, fetch_source_content
from backend.llm import safe_invoke
from backend.parsing import parse_json_response
from backend.utils.text_chunker import chunk_text

logger = logging.getLogger(__name__)


def _build_instruction(sources_with_content: list) -> str:
    blocks = []
    for i, item in enumerate(sources_with_content, start=1):
        blocks.append(
            f"--- SOURCE {i} ---\n"
            f"source_id: {item['url']}\n"
            f"title: {item['title']}\n"
            f"url: {item['url']}\n"
            f"content:\n{item['content']}\n"
        )
    joined = "\n".join(blocks)

    return f"""For EACH source below, extract:
a) metrics — numeric results, accuracy %, BLEU, F1, latency, etc.
b) datasets — named benchmarks/datasets mentioned
c) key_findings — 2-3 concise findings (1 sentence each)
d) quotes — up to 2 verbatim sentences from the source

Each source object MUST NOT exceed 300 tokens. If over budget, cut key_findings first, then quotes.

{joined}

Return ONLY this JSON array, no prose, no markdown fences:
[{{"source_id": "...", "title": "...", "url": "...", "metrics": [], "datasets": [], "key_findings": [], "quotes": []}}]"""


def extraction_node(state: dict, llm) -> dict:
    validated_sources = state.get("validated_sources", [])
    if not validated_sources:
        logger.warning("Extractor: no validated sources to process.")
        return {"evidence": []}

    sources_with_content = []
    for source in validated_sources:
        content = fetch_source_content(source)
        chunks = chunk_text(content, max_tokens=800) if content else []
        sources_with_content.append({
            "url": source["url"],
            "title": source.get("title", "Untitled"),
            "content": chunks[0] if chunks else "",
        })

    logger.info(
        "Extractor: fetched content for %d sources, running one batched LLM call",
        len(sources_with_content),
    )
    messages = [
        {"role": "system", "content": EXTRACTOR_SYSTEM_PROMPT},
        {"role": "user", "content": _build_instruction(sources_with_content)},
    ]
    raw = safe_invoke(llm, messages)
    evidence = parse_json_response(raw)
    if not isinstance(evidence, list):
        evidence = []

    logger.info("Extractor produced evidence for %d sources", len(evidence))
    return {"evidence": evidence}