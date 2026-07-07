"""
parsing.py
----------
Shared JSON-extraction helper for all LLM-driven nodes.
"""
import json
import re
import logging

logger = logging.getLogger(__name__)


def parse_json_response(raw: str):
    """Strip markdown fences and parse the LLM's JSON output, with a
    last-resort regex fallback if the model wrapped it in prose."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        logger.error("Failed to parse JSON from LLM response: %s", cleaned[:300])
        return {}