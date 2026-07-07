"""
extractor_agent.py
------------------
Extractor Agent — Technical Evidence Extractor (persona + deterministic fetch)

Fetching content is deterministic (no LLM): PDF via PDFExtractorTool for
arXiv/paper sources, webpage via WebParserTool otherwise. The single
LLM call (batched across all sources) happens in tasks/extraction_task.py.
"""
import logging
from typing import Dict, Any

from backend.tools.pdf_extractor import PDFExtractorTool
from backend.tools.web_parser import WebParserTool

logger = logging.getLogger(__name__)

_pdf_tool = PDFExtractorTool()
_web_tool = WebParserTool()

EXTRACTOR_SYSTEM_PROMPT = """You are a Technical Evidence Extractor — a technical analyst who distills dense research papers into machine-readable evidence records.

For each source's fetched text, extract ONLY: numeric metrics, dataset names, methodology snippets, up to 2 verbatim quotes, and key findings. Discard boilerplate, ads, navigation text.

You never paraphrase a quote — if you quote something, it is verbatim from the source text. If a metric or dataset name is absent, leave the field empty rather than guessing.

You are ruthlessly concise: never exceed 300 tokens per source object.

You return ONLY valid JSON, never prose, never markdown fences."""


def fetch_source_content(source: Dict[str, Any]) -> str:
    """Deterministic content fetch — no LLM involved."""
    url = source.get("url", "")
    source_type = source.get("source_type", "web")

    try:
        if source_type == "paper" and "arxiv.org" in url:
            return _pdf_tool._run(url=url)
        return _web_tool._run(url=url)
    except Exception as exc:
        logger.warning("Fetch failed for %s: %s — falling back to snippet", url, exc)
        return source.get("snippet", "")