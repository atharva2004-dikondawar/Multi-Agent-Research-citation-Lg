"""
validation_task.py
-------------------
Task logic for the Validator node. One batched LLM call scores ALL
raw sources at once and keeps the top 5.
"""
import json
import logging

from backend.agents.validator_agent import VALIDATOR_SYSTEM_PROMPT
from backend.llm import safe_invoke
from backend.parsing import parse_json_response

logger = logging.getLogger(__name__)

RUBRIC = """Score each source 1-10 using this rubric:

Credibility (0-4): 4=arXiv/IEEE/ACL/NeurIPS/ICML/ICLR/CVPR, 3=other peer-reviewed venue or well-known GitHub repo, 2=official docs, 1=general technical web page, 0=blog/Medium/listicle
Recency (0-3): 3=last 12 months, 2=1-2 years, 1=2-5 years, 0=older than 5 years or no date
Technical depth (0-3): 3=quantitative results/datasets/algorithms in snippet, 2=methodology but no numbers, 1=descriptive/conceptual, 0=vague or marketing-like

Keep only the TOP 5 sources by total score. On ties, prefer the more recent one."""


def _build_instruction(raw_sources: list) -> str:
    trimmed_sources = [
        {**s, "snippet": (s.get("snippet") or "")[:200]}
        for s in raw_sources
    ]
    return f"""{RUBRIC}

SOURCES (JSON array):
{json.dumps(trimmed_sources, indent=2)}

Return ONLY this JSON object, no prose, no markdown fences:
{{"validated_sources": [{{"title": "...", "url": "...", "source_type": "...", "published_date": "...", "snippet": "...", "score": 0, "rationale": "..."}}]}}"""


def validation_node(state: dict, llm) -> dict:
    raw_sources = state.get("raw_sources", [])
    if not raw_sources:
        logger.warning("Validator: no raw sources to score.")
        return {"validated_sources": []}
    
    # Cap input size to avoid exceeding the model's context window
    MAX_SOURCES_FOR_VALIDATION = 25
    if len(raw_sources) > MAX_SOURCES_FOR_VALIDATION:
        logger.info("Trimming %d sources down to %d before validation", len(raw_sources), MAX_SOURCES_FOR_VALIDATION)
        raw_sources = raw_sources[:MAX_SOURCES_FOR_VALIDATION]
        
    logger.info("Validator: scoring %d sources", len(raw_sources))
    messages = [
        {"role": "system", "content": VALIDATOR_SYSTEM_PROMPT},
        {"role": "user", "content": _build_instruction(raw_sources)},
    ]
    raw = safe_invoke(llm, messages, max_tokens_override=2048)
    parsed = parse_json_response(raw)
    validated = parsed.get("validated_sources", [])[:5]

    logger.info("Validator kept %d sources", len(validated))
    return {"validated_sources": validated}