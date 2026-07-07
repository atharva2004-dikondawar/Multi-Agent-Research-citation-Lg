"""
main.py
-------
CLI entry point for the LangGraph Research Citation Engine.

Usage:
    python -m backend.main --topic "attention mechanisms in transformers"
"""
import argparse, logging, os, sys, time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from backend.graph import build_graph
from backend.llm import detect_provider

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler("research_crew.log", mode="a")])
logger = logging.getLogger(__name__)


def _check_env():
    provider = detect_provider()
    if provider == "unknown":
        logger.error("No LLM credentials found. Set OPENAI_API_KEY or HF_TOKEN.")
        sys.exit(1)
    if not os.getenv("EXA_API_KEY"):
        logger.error("EXA_API_KEY is required but not set.")
        sys.exit(1)
    if not os.getenv("TAVILY_API_KEY"):
        logger.warning("TAVILY_API_KEY not set — fallback search unavailable.")
    logger.info("LLM provider: %s", provider)


def _save_report(report: str) -> Path:
    p = Path(os.getenv("OUTPUT_FILE", "research_report.md"))
    p.write_text(report, encoding="utf-8")
    logger.info("Saved → %s", p.resolve())
    return p


def main():
    _check_env()
    parser = argparse.ArgumentParser(description="Research Engine (LangGraph)")
    parser.add_argument("--topic", type=str, default=None)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()
    if args.output: os.environ["OUTPUT_FILE"] = args.output

    topic = args.topic or input("\nEnter research topic: ").strip()
    if not topic:
        logger.error("No topic.")
        sys.exit(1)

    logger.info("="*60); logger.info("Pipeline start | %s", topic); logger.info("="*60)
    t0 = time.time()

    graph = build_graph()
    final_state = graph.invoke({"topic": topic})
    report = final_state.get("report", "")

    elapsed = time.time() - t0
    logger.info("Done in %.1fs", elapsed)

    report += f"\n\n---\n*Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} · {elapsed:.0f}s*\n"
    path = _save_report(report)

    print("\n" + "="*60 + "\n" + report + "\n" + "="*60)
    print(f"\nSaved: {path.resolve()}")


if __name__ == "__main__":
    main()