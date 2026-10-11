# AGENTS.md

## Repository Overview

**Intelligent Portfolio Analyst ("AlphaBot")** is a Streamlit web application that gives retail investors
institutional-style portfolio analysis. A user uploads a Zerodha-style holdings statement (CSV/XLSX), and
a multi-agent LangGraph pipeline enriches every holding with live market data and AI-generated verdicts,
then renders a dashboard, per-stock deep-dive, personalized news feed, "what-if" scenario tool, and a
standalone NSE stock screener.

## Project Description

- **What it does:** Parses an uploaded portfolio file, fetches live fundamentals/technicals/price history
  per stock via `yfinance`, asks an LLM (Groq) for a fundamental verdict and a technical/sentiment verdict,
  synthesizes those plus beta into a final Buy/Hold/Sell recommendation with urgency and reasoning,
  summarizes recent news per stock, aggregates portfolio-level metrics (P&L, weighted-beta risk profile,
  sector allocation), and renders everything in a Streamlit UI.
- **Main purpose/goals:** Democratize deep financial analysis that is normally only available to
  institutional analysts, using an inspectable, modular "Chain of Thought" agent pipeline rather than a
  single opaque LLM call.
- **Key technologies:**
  - **Streamlit** — UI/front end and app entry point (`main_app.py`).
  - **LangGraph** (`langgraph.graph.StateGraph`) — orchestrates the agent workflow as a stateful directed graph.
  - **langchain-groq / Groq API** — LLM calls, model `meta-llama/llama-4-scout-17b-16e-instruct`.
  - **yfinance** — live market data (fundamentals, technicals, price history, beta, news).
  - **newsapi-python** — fallback news source when `yfinance` news is insufficient.
  - **pandas / openpyxl / pdfplumber** — parsing CSV, Excel, and PDF portfolio statements.
  - **Plotly** — charts (allocation pies, price history, comparisons).
  - **python-dotenv** — loads `.env` for local API keys (`GROQ_API_KEY`, `NEWS_API_KEY`).

## Architecture Overview

The backend is a **LangGraph state machine** (`graph/graph_orchestrator.py`) with one shared `AppState`
dict threaded through every node. Streamlit's `main_app.py` streams the graph (`app.stream(...)`) and
updates a live status widget as each node completes.

**Pipeline (sequential graph nodes / agents in `agents/`):**

1. **`ingest_portfolio`** → `portfolio_ingestion_agent.py` — detects file type (`.csv`/`.xlsx`/`.pdf`) and
   delegates to the matching parser in `parsers/`.
2. **`validate_ingestion`** → `validation_agent.py` — guards that ingestion produced a well-formed
   `{"stocks": [...]}` structure before continuing; short-circuits to `END` on error via a conditional edge.
3. **`enrich_stocks`** → `stock_analysis_agent.py` — the core engine. For each holding: fetches live data
   via `utils/data_fetchers.py` (the 4 yfinance calls per stock run concurrently in a thread pool, see
   `fetch_stock_data()`), then runs sequential Groq LLM calls (fundamental verdict → technical/sentiment
   verdict → final synthesis with urgency + reason), extracting JSON from LLM responses defensively.
   Holdings themselves are still processed one at a time to stay within Groq's rate limits. All three
   LLM calls go through `utils/llm_retry.invoke_with_retry()`, which retries transient Groq failures
   (rate limits, timeouts, connection errors, 5xx) with exponential backoff before giving up.
4. **`news_analyzer`** → `news_analysis_agent.py` — fetches recent headlines per stock (yfinance first,
   NewsAPI fallback) and asks the LLM to summarize each into one sentence.
5. **`report_generator`** → `report_generation_agent.py` — aggregates stock analysis + news + errors into
   the single `final_report` dict consumed by the UI (and by `utils/portfolio_aggregator.py` for
   portfolio-level metrics: total investment/value/P&L, weighted-beta risk profile, sector allocation).

Conditional edges (`should_continue`) let any upstream agent abort the graph early by setting
`state["error"]`, which the UI surfaces instead of partial results.

A separate, non-graph feature — the **Stock Screener** (`agents/screener_agent.py`, driven by
`utils/stock_universe.py`'s static NSE ticker list) — lets a user analyze any individual NSE stock
(pros/cons + peer comparison) outside the portfolio-upload flow.

**Data flow:** uploaded file → parser → raw holdings list → per-stock enrichment (market data + LLM
verdicts) → news summaries → aggregated report dict → Streamlit tabs (Dashboard, Stock Deep-Dive,
Personalized News, What-If Analysis, Detailed Stock Analysis/Screener).

## Directory Structure

```
main_app.py                     Streamlit entry point: UI, tabs, styling, triggers run_graph()
graph/
  graph_orchestrator.py         Builds/compiles the LangGraph StateGraph, defines AppState & run_graph()
agents/
  portfolio_ingestion_agent.py  Detects file type, dispatches to a parser
  validation_agent.py           Validates parsed portfolio_data shape
  stock_analysis_agent.py       Per-stock data gathering + chain-of-thought LLM analysis
  news_analysis_agent.py        Per-stock news fetch (yfinance/NewsAPI) + LLM summarization
  report_generation_agent.py    Final report assembly
  screener_agent.py             Standalone single-stock screener (pros/cons, peer comparison)
parsers/
  csv_parser.py, excel_parser.py, pdf_parser.py   Normalize uploaded files to {"stocks": [...]}
utils/
  data_fetchers.py              All yfinance calls: fundamentals, technicals, price history, beta, news
  portfolio_aggregator.py       Portfolio-level metrics: P&L, weighted-beta risk profile, sector allocation
  stock_universe.py             Static list of NSE tickers used by the screener's dropdown (see scripts/)
  config.py                     get_secret(): resolves API keys from st.secrets or os.getenv (.env)
  llm_retry.py                  invoke_with_retry(): exponential-backoff retry for transient Groq errors
scripts/
  refresh_stock_universe.py     Offline maintenance script to regenerate utils/stock_universe.py from NSE
tests/
  conftest.py, fakes.py         Shared pytest fixtures (st.session_state) and a FakeLLM test double
  test_*.py                     Unit tests per module, mirroring agents/, parsers/, utils/
requirements.txt                Runtime Python dependencies (no pinned versions)
requirements-dev.txt            Adds pytest + pytest-mock on top of requirements.txt
pytest.ini                      Configures pytest to discover tests/ with the repo root on sys.path
README.md                       Feature overview, architecture narrative, setup/usage instructions
.cph/                           Leftover tooling artifact, not part of the app
```

**Entry point:** `streamlit run main_app.py`
**Secrets:** expects `GROQ_API_KEY` and `NEWS_API_KEY` from either a `.env` file (loaded by
`python-dotenv`'s `load_dotenv()`) or Streamlit secrets (`.streamlit/secrets.toml`). All agents resolve
secrets through `utils/config.get_secret()`, which checks `st.secrets` first and falls back to
`os.getenv(...)`, so a plain `.env`-only setup works without also needing a `secrets.toml`. In
`news_analysis_agent.py`, a missing/invalid `NEWS_API_KEY` only disables the NewsAPI fallback (logged as
a non-fatal analysis error) — the yfinance-based primary news path and `GROQ_API_KEY`-based summarization
still run.

## Development Workflow

### Setup
```bash
python -m venv venv
source venv/bin/activate            # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```
Create a `.env` in the project root:
```
GROQ_API_KEY="your_groq_api_key_here"
NEWS_API_KEY="your_news_api_key_here"
```
(Streamlit also supports `.streamlit/secrets.toml` for the same keys — either source works, see
`utils/config.py`.)

### Run
```bash
streamlit run main_app.py
```
Upload a `.csv` or `.xlsx` holdings file containing columns: `Instrument`, `Qty`, `Avg. cost`, `Invested`,
`Cur. val`, `P&L` (header matching is case/format tolerant — see `parsers/csv_parser.py` /
`excel_parser.py`). PDF parsing (`parsers/pdf_parser.py`) is a generic regex template
(`HOLDINGS_LINE_PATTERN`) and typically needs the pattern adapted to a specific broker's PDF layout before
it will reliably match; use the module's `_debug_dump_text()` helper to inspect what `pdfplumber` extracts
from a sample statement when adapting it.

### Testing
```bash
pip install -r requirements-dev.txt
pytest
```
A `pytest` suite lives in `tests/`, mirroring `agents/`, `parsers/`, and `utils/` one test module per
source module (including `tests/test_llm_retry.py` for the backoff/retry helper). `yfinance` and
`ChatGroq` calls are mocked (via `pytest-mock`'s `mocker` fixture and the shared `tests/fakes.FakeLLM`
double) so tests run offline, deterministically, and without needing real API keys. `tests/conftest.py`
provides a `st.session_state.analysis_logs` fixture since several agents write to it directly. When
adding new agent logic, follow the existing pattern: patch `data_fetchers`/`ChatGroq` at their import
site inside the agent module (e.g. `agents.stock_analysis_agent.ChatGroq`), not at `langchain_groq.ChatGroq`.

### Lint / Format
No linter, formatter, or pre-commit config is currently configured in this repo (no `.flake8`,
`pyproject.toml`, or `ruff.toml`). Follow the existing style already in the codebase (plain PEP 8,
docstrings on every function/agent) rather than introducing a new tool without checking with the user first.

### Notes for agents working in this codebase
- `requirements.txt` has no pinned versions; be cautious about relying on version-specific API behavior.
- Several agent functions call `st.session_state.analysis_logs.append(...)` directly, coupling backend
  agents to Streamlit session state — this is intentional for the live status/log UI, not a bug.
- LLM responses are parsed with a best-effort regex/JSON extractor (`extract_json_from_response` in
  `stock_analysis_agent.py`); if you change prompts, keep output JSON-fenced (```` ```json ... ``` ````) to
  stay compatible with this extractor.
- Tickers are NSE symbols; the app appends `.NS` before every `yfinance` call (e.g. `RELIANCE` → `RELIANCE.NS`).
- `utils/stock_universe.py` is intentionally static (no runtime dependency on NSE being reachable). Run
  `python scripts/refresh_stock_universe.py` periodically and commit the regenerated file to pick up newly
  listed/delisted symbols; the script is never imported or executed by the running app.
- `stock_analysis_agent.fetch_stock_data()` parallelizes only the 4 yfinance calls per stock (I/O-bound,
  safe to run concurrently). The Groq LLM calls remain sequential per stock — do not parallelize those
  without also reviewing `utils/llm_retry.py`'s backoff timing, since Groq's free tier has strict
  per-minute request caps.
- All Groq `chain.invoke(...)` calls (in `stock_analysis_agent.py`, `news_analysis_agent.py`, and
  `screener_agent.py`) go through `utils/llm_retry.invoke_with_retry()` instead of calling `.invoke()`
  directly. It retries `RateLimitError`, `APIConnectionError`, `APITimeoutError`, and
  `InternalServerError` with exponential backoff (2s, 4s, 8s, ...) before giving up and letting the
  exception propagate to the caller's existing per-stock/per-article try/except. Non-retryable errors
  (bad request, auth failure, etc.) propagate immediately. When adding a new LLM call site, use this
  helper rather than calling `chain.invoke(...)` directly.
