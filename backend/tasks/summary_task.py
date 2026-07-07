"""
summary_task.py
---------------
Task logic for the Synthesizer node — the terminal step. One LLM call
turns the evidence array into the final Markdown report.
"""
import json
import logging

from backend.agents.synthesizer_agent import SYNTHESIZER_SYSTEM_PROMPT
from backend.llm import safe_invoke

logger = logging.getLogger(__name__)


def _build_instruction(topic: str, evidence: list) -> str:
    return f"""RESEARCH TOPIC: {topic}

EVIDENCE (JSON array, 1-based index = citation number):
{json.dumps(evidence, indent=2)}

HARD RULES:
1. ONLY cite sources whose url appears in the evidence array.
2. NEVER add facts not present in the evidence.
3. Every factual sentence ends with an inline citation [N].
4. If evidence for a section is absent, omit that section entirely.

Produce Markdown in this structure:

# Research Summary: {topic}

## Key Insights
1. **<Headline>**
   <Evidence: 2-4 sentences.>
   *Source: [1]*

(minimum 3 insights)

## Methodology Overview  (omit if no methodology evidence)
<Concise description from key_findings.>

## Benchmarks & Metrics  (omit if no metrics evidence)
| Metric | Value | Source |
|--------|-------|--------|
| ...    | ...   | [N]    |

## Sources
[1] <title>
    <url>

Rules: source index [N] = position in evidence array (1-based). Copy URLs verbatim. No separate 'References' section."""


def summary_node(state: dict, llm) -> dict:
    topic = state.get("topic", "")
    evidence = state.get("evidence", [])

    logger.info("Synthesizer: writing report for '%s' from %d evidence records", topic, len(evidence))
    messages = [
        {"role": "system", "content": SYNTHESIZER_SYSTEM_PROMPT},
        {"role": "user", "content": _build_instruction(topic, evidence)},
    ]
    report = safe_invoke(llm, messages)

    return {"report": report}