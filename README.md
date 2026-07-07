# Multi-Agent Research Citation Engine (LangGraph Edition)

A production-grade AI research assistant built with **LangGraph** (Python) and a **React + Vite** frontend.
Enter any research topic and receive a structured Markdown report with accurate citations, extracted evidence, and verified references.

Originally built with CrewAI, migrated to LangGraph for lower LLM call overhead and finer control over the pipeline — see [Migration Notes](#migration-notes) below.

---

## What It Does

1. **Planner node** decomposes your topic into 4–6 targeted search queries (1 LLM call)
2. **Search node** retrieves up to 8 sources per query from arXiv, IEEE, ACL, GitHub, and official docs via Exa and Tavily APIs (0 LLM calls — deterministic)
3. **Validator node** scores every source (1–10) on credibility, recency, and technical depth — keeps only the top 5 (1 batched LLM call)
4. **Extractor node** fetches each source (PDF or webpage) and extracts metrics, datasets, findings, and verbatim quotes (0 LLM calls for fetching + 1 batched LLM call for extraction)
5. **Synthesizer node** merges all evidence into a structured Markdown report with inline citations — no hallucination, every claim is grounded (1 LLM call)

**Total: 4 LLM calls per full research run** — designed to work reliably on free-tier LLM providers (Hugging Face Inference Providers) without hitting rate limits.

---

## Architecture
User Topic
→ Planner Node    (1 LLM call: generate queries)
→ Search Node      (0 LLM calls: Exa + Tavily, deterministic)
→ Validator Node  (1 LLM call: score & filter to top 5)
→ Extractor Node  (0 LLM calls: fetch content, 1 LLM call: extract evidence)
→ Synthesizer Node (1 LLM call: produce final Markdown report)

All nodes communicate via a shared **LangGraph `StateGraph`** (`GraphState` TypedDict) — never raw documents between steps.
The FastAPI backend streams node progress to the React frontend via **Server-Sent Events (SSE)**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| AI Orchestration | LangGraph (StateGraph) |
| LLM | Hugging Face Inference Providers **or** OpenAI |
| Search | Exa neural search (primary) + Tavily (fallback) |
| PDF parsing | PyMuPDF (`fitz`) |
| Web parsing | BeautifulSoup4 |
| Frontend | React 18 + Vite + TypeScript |
| UI | shadcn/ui + Tailwind CSS |
| Streaming | Server-Sent Events (SSE) |
| Deployment | Render (backend web service + static frontend) |

---

## Quick Start (Windows)

### 1. Clone & set up the backend

```powershell
git clone <repo-url>
cd research-engine-langgraph

python -m venv marcl
.\marcl\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

### 2. Configure environment

Create a `.env` file in the **project root** (same level as `backend/`, not inside it):

```dotenv
LLM_PROVIDER=huggingface
HF_TOKEN=hf_your_token_here
HF_MODEL=meta-llama/Llama-3.1-8B-Instruct:together

# OPENAI_API_KEY=sk-your_key_here
# OPENAI_MODEL=gpt-4o

LLM_TEMPERATURE=0.3

EXA_API_KEY=your_exa_key_here
TAVILY_API_KEY=your_tavily_key_here

OUTPUT_FILE=research_report.md
ALLOWED_ORIGINS=
```

### 3. Run the backend

**Important:** run from the **project root**, not from inside `backend/` — the code uses absolute imports (`from backend.tools... import ...`).

```powershell
uvicorn backend.app:app --reload --port 8000
```

### 4. Run the frontend

Open a **second terminal**:

```powershell
cd frontend
npm install
npm run dev
```

Open the printed local URL (typically `http://localhost:8080`) — Vite proxies `/api/*` to the FastAPI backend automatically.

### 5. CLI usage (no server, no frontend)

```powershell
python -m backend.main --topic "attention mechanisms in transformers"
```
Writes the report to `research_report.md` in the project root.

---

## Verified Working Environment

- Python **3.11.7**
- Node.js **18.x**
- HF router: `https://router.huggingface.co/v1`
- Tested model: `meta-llama/Llama-3.1-8B-Instruct:together`
- Backend deps: pinned exactly via `pip freeze` in `backend/requirements.txt`
- Frontend deps: pinned via `frontend/package-lock.json`

---

## Project Structure
research-engine-langgraph/
├── backend/
│   ├── graph_state.py             # Shared LangGraph state schema
│   ├── llm.py                     # LLM provider detection + rate-limit-safe invoke
│   ├── parsing.py                 # Shared JSON-extraction helper
│   ├── graph.py                   # StateGraph wiring (5 nodes, linear edges)
│   ├── app.py                     # FastAPI server with SSE streaming
│   ├── main.py                    # CLI entry point
│   ├── requirements.txt
│   ├── agents/
│   │   ├── planner_agent.py       # System prompt: Research Strategist
│   │   ├── search_agent.py        # Deterministic Exa/Tavily orchestration
│   │   ├── validator_agent.py     # System prompt: Source Quality Evaluator
│   │   ├── extractor_agent.py     # System prompt + deterministic content fetch
│   │   └── synthesizer_agent.py   # System prompt: Research Writer
│   ├── tasks/
│   │   ├── planning_task.py       # Planner node logic (1 LLM call)
│   │   ├── search_task.py         # Search node logic (0 LLM calls)
│   │   ├── validation_task.py     # Validator node logic (1 LLM call)
│   │   ├── extraction_task.py     # Extractor node logic (1 batched LLM call)
│   │   └── summary_task.py        # Synthesizer node logic (1 LLM call)
│   ├── tools/
│   │   ├── search_tool.py         # Exa + Tavily search tools
│   │   ├── pdf_extractor.py       # PyMuPDF PDF text extractor
│   │   └── web_parser.py          # BeautifulSoup webpage parser
│   └── utils/
│       ├── token_utils.py         # count_tokens, truncate_text
│       └── text_chunker.py        # chunk_text with overlap
├── frontend/
│   ├── src/
│   │   ├── api/client.ts
│   │   ├── hooks/
│   │   │   ├── useJobStream.ts
│   │   │   └── useElapsedTime.ts
│   │   ├── pages/
│   │   │   ├── Index.tsx
│   │   │   └── ResearchPage.tsx
│   │   └── components/
│   │       ├── PipelineSidebar.tsx
│   │       └── ReportViewer.tsx
│   ├── package.json
│   └── vite.config.ts
├── render.yaml
└── README.md

---

## Token & LLM-Call Safety

| Layer | Limit | Mechanism |
|---|---|---|
| Document download | 10 MB | Streaming cap in `pdf_extractor.py` |
| Extracted text per source | 3 000 chars | Hard truncation in tools |
| Text chunks | 800 tokens | `chunk_text()` in `text_chunker.py` |
| Evidence per source | 300 tokens | Prompt instruction in `extraction_task.py` |
| LLM calls per run | 4 total | Deterministic search + extractor-fetch, batched validator + extractor-evidence calls |
| LLM call retries | Exponential backoff, 5 attempts | `tenacity` in `llm.py` |

---

## Output Format

```markdown
# Research Summary: <Topic>

## Key Insights

1. **<Headline>**
   <Supporting evidence, 2–4 sentences.>
   *Source: [1]*

## Methodology Overview
<Concise description drawn from extracted methodology snippets.>

## Benchmarks & Metrics
| Metric | Value | Source |
|--------|-------|--------|
| ...    | ...   | [1]    |

## Sources

[1] <Title>
    <URL>
```

---

## Deployment (Render)

This project deploys as two separate Render services (backend + static frontend), defined in `render.yaml`.

**Critical note:** because the backend uses absolute imports (`backend.*`), the backend service's `rootDir` must be the **project root**, not `backend/` — with `startCommand: uvicorn backend.app:app --host 0.0.0.0 --port $PORT`.

### Deploy steps
1. Push this repo to GitHub.
2. In Render, create a new **Blueprint** from `render.yaml`.
3. Set the backend env vars marked `sync: false` in the Render dashboard: `HF_TOKEN`, `EXA_API_KEY`, `TAVILY_API_KEY`.
4. Once the frontend deploys, copy its Render URL and set it as `ALLOWED_ORIGINS` on the backend service.
5. Once the backend deploys, copy its Render URL + `/api` and set it as `VITE_API_URL` on the frontend service, then trigger a frontend redeploy.

---

## Extending the System

| Goal | Where to change |
|---|---|
| Add a new search backend | `tools/search_tool.py` — create a new `BaseTool` subclass |
| Change number of top sources | `tasks/validation_task.py` — update the rubric/prompt instruction |
| Support local LLMs (Ollama) | `llm.py` `build_llm()` — add an `ollama` branch pointing `ChatOpenAI` at a local base_url |
| Add persistence across restarts | `graph.py` — use LangGraph checkpointing instead of the in-memory `JOBS` dict in `app.py` |
| Export to PDF | Post-process `research_report.md` with `pandoc` or `weasyprint` |
| Add a new node | Create an agent (system prompt) + task (node logic) file, wire into `graph.py` |

---

## Migration Notes

This project was originally built with **CrewAI** (sequential `Agent`/`Task`/`Crew` pattern) and migrated to **LangGraph** to:
- Reduce LLM call count from CrewAI's ReAct-style tool-calling loops (`max_iter=15–20` per agent) down to a fixed **4 LLM calls per run** — critical for running reliably on free-tier LLM providers.
- Replace implicit CrewAI task context-passing with an explicit, typed `GraphState` shared across nodes.
- Gain direct control over which steps use an LLM at all — Search and the content-fetch half of Extraction are now pure deterministic Python, with no LLM reasoning overhead.

Tools (`search_tool.py`, `pdf_extractor.py`, `web_parser.py`) and utils (`token_utils.py`, `text_chunker.py`) required no logic changes — only an import swap from `crewai.tools.BaseTool` to `langchain_core.tools.BaseTool`, since they were already Pydantic-based and framework-agnostic by design.

---

## Requirements

- Python 3.11.7
- Node.js ≥ 18
- Hugging Face token **or** OpenAI API key
- Exa API key (free tier at [exa.ai](https://exa.ai))
- Tavily API key (optional, free tier at [tavily.com](https://tavily.com))