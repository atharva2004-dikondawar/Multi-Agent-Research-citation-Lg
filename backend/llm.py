"""
llm.py
------
LLM provider auto-detection (OpenAI vs HuggingFace free tier) +
a rate-limit-safe invoke wrapper used by every task node.
"""
import os
import logging
from langchain_openai import ChatOpenAI
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = logging.getLogger(__name__)


def detect_provider() -> str:
    explicit = os.getenv("LLM_PROVIDER", "").strip().lower()
    if explicit in ("openai", "huggingface"):
        return explicit
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("HF_TOKEN"):
        return "huggingface"
    return "unknown"


def build_llm() -> ChatOpenAI:
    provider = detect_provider()
    temp = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    if provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        logger.info("LLM: OpenAI | model: %s | temp: %.1f", model, temp)
        return ChatOpenAI(model=model, api_key=os.getenv("OPENAI_API_KEY"), temperature=temp, max_tokens=max_tokens)

    if provider == "huggingface":
        model = os.getenv("HF_MODEL", "meta-llama/Llama-3.1-8B-Instruct:novita")
        logger.info("LLM: HuggingFace Inference Providers | model: %s | temp: %.1f", model, temp)
        return ChatOpenAI(
            model=model,
            api_key=os.getenv("HF_TOKEN"),
            base_url="https://router.huggingface.co/v1",
            temperature=temp,
            max_tokens=max_tokens,
        )

    logger.error("No LLM credentials found. Set OPENAI_API_KEY or HF_TOKEN.")
    raise RuntimeError("No LLM credentials found. Set OPENAI_API_KEY or HF_TOKEN.")


@retry(
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def safe_invoke(llm, messages: list, max_tokens_override: int = None) -> str:
    """Invoke the LLM with exponential backoff — critical for free-tier
    rate limits (HF Inference API 429s especially)."""
    if max_tokens_override is not None:
        resp = llm.invoke(messages, max_tokens=max_tokens_override)
    else:
        resp = llm.invoke(messages)
    return resp.content